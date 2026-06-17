"""Unit tests for tools/ingest_email.py. Stdlib unittest, no network."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ingest_email  # noqa: E402
import pipeline  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "email_alerts_sample.json"
TODAY = "2026-06-17"


def _load_fixture() -> list[dict]:
    with FIXTURE.open(encoding="utf-8") as fh:
        return json.load(fh)


class FieldExtractionTests(unittest.TestCase):
    def test_clean_title_strips_prefixes(self) -> None:
        self.assertEqual(
            ingest_email.clean_title("New Opportunity: Dormitory Mattresses"),
            "Dormitory Mattresses",
        )
        self.assertEqual(
            ingest_email.clean_title("Fwd: Bid Notification - Twin Mattresses"),
            "Twin Mattresses",
        )

    def test_clean_title_empty_falls_back(self) -> None:
        self.assertEqual(ingest_email.clean_title(""), "")

    def test_source_for_sender(self) -> None:
        self.assertEqual(
            ingest_email.source_for_sender("notifications@gobonfire.com"), "Bonfire"
        )
        # region4esc subdomain on ionwave.net must win over bare ionwave.net.
        self.assertEqual(
            ingest_email.source_for_sender("noreply@region4esc.ionwave.net"),
            "Region 4 ESC (OMNIA)",
        )
        # Unknown sender falls back to the bare domain.
        self.assertEqual(
            ingest_email.source_for_sender("bids@cityofsomewhere.gov"),
            "cityofsomewhere.gov",
        )

    def test_normalize_date_formats(self) -> None:
        self.assertEqual(ingest_email.normalize_date("June 30, 2026"), "2026-06-30")
        self.assertEqual(ingest_email.normalize_date("6/25/2026"), "2026-06-25")
        self.assertEqual(ingest_email.normalize_date("2026-07-10"), "2026-07-10")
        self.assertEqual(ingest_email.normalize_date("not a date"), "")

    def test_extract_due_date(self) -> None:
        self.assertEqual(
            ingest_email.extract_due_date("Submissions close June 30, 2026 at 2 PM"),
            "2026-06-30",
        )
        self.assertEqual(ingest_email.extract_due_date("no date present"), "")

    def test_extract_url_prefers_platform_and_skips_unsubscribe(self) -> None:
        body = (
            "View: https://city.bonfirehub.com/opportunities/1\n"
            "Unsubscribe: https://gobonfire.com/unsubscribe?x=1"
        )
        self.assertEqual(
            ingest_email.extract_url(body), "https://city.bonfirehub.com/opportunities/1"
        )

    def test_extract_url_none(self) -> None:
        self.assertEqual(ingest_email.extract_url("no links here"), "")


class ParseMessageTests(unittest.TestCase):
    def test_parse_full_message(self) -> None:
        msg = _load_fixture()[0]  # Bonfire
        row = ingest_email.parse_message(msg, TODAY)
        self.assertIsNotNone(row)
        self.assertEqual(row["source"], "Bonfire")
        self.assertEqual(row["title"], "Dormitory Mattresses and Bed Frames")
        self.assertEqual(row["portal_url"], "https://city.bonfirehub.com/opportunities/12345")
        self.assertEqual(row["due_date"], "2026-06-30")
        self.assertEqual(row["status"], "watching")
        self.assertTrue(set(row).issuperset(set(pipeline.CANONICAL_HEADER)))

    def test_parse_skips_no_title(self) -> None:
        msg = _load_fixture()[-1]  # empty subject
        self.assertIsNone(ingest_email.parse_message(msg, TODAY))

    def test_id_is_stable_for_same_url(self) -> None:
        msgs = _load_fixture()
        a = ingest_email.parse_message(msgs[0], TODAY)
        b = ingest_email.parse_message(msgs[3], TODAY)  # same opportunity url
        self.assertEqual(a["opportunity_id"], b["opportunity_id"])


class GraphNormalizeTests(unittest.TestCase):
    def test_normalize_html_body_and_sender(self) -> None:
        graph_msg = {
            "id": "AAMk-123",
            "subject": "New Opportunity: Twin Mattresses",
            "from": {"emailAddress": {"name": "Bonfire", "address": "no-reply@gobonfire.com"}},
            "receivedDateTime": "2026-06-16T14:05:00Z",
            "body": {"contentType": "html", "content": "<p>View: <a href='https://x.bonfirehub.com/o/9'>link</a></p>"},
            "bodyPreview": "View: link",
        }
        norm = ingest_email.normalize_graph_message(graph_msg)
        self.assertEqual(norm["sender"], "no-reply@gobonfire.com")
        self.assertEqual(norm["subject"], "New Opportunity: Twin Mattresses")
        self.assertEqual(norm["date"], "2026-06-16T14:05:00Z")
        self.assertIn("bonfirehub.com/o/9", norm["body"])
        self.assertNotIn("<a", norm["body"])  # HTML stripped

    def test_normalize_feeds_parser(self) -> None:
        graph_msg = {
            "id": "AAMk-456",
            "subject": "Bid Notification - Institutional Mattresses",
            "from": {"emailAddress": {"address": "bids@demandstar.com"}},
            "receivedDateTime": "2026-06-16T09:00:00Z",
            "body": {"contentType": "text", "content": "Response due 6/25/2026.\nhttps://www.demandstar.com/app/bid/1"},
        }
        row = ingest_email.parse_message(ingest_email.normalize_graph_message(graph_msg), TODAY)
        self.assertEqual(row["source"], "DemandStar")
        self.assertEqual(row["due_date"], "2026-06-25")
        self.assertEqual(row["portal_url"], "https://www.demandstar.com/app/bid/1")


class IngestTests(unittest.TestCase):
    def test_partition_counts(self) -> None:
        new_rows, dupes, skipped, rejected = ingest_email.ingest(_load_fixture(), [], TODAY)
        self.assertEqual(len(new_rows), 3)   # bonfire, region4, demandstar (all mattress)
        self.assertEqual(len(dupes), 1)      # bonfire duplicate
        self.assertEqual(len(skipped), 1)    # empty subject
        self.assertEqual(len(rejected), 0)   # all fixture items are mattress-relevant

    def test_dedup_against_existing(self) -> None:
        msgs = _load_fixture()
        first = ingest_email.parse_message(msgs[0], TODAY)
        existing = [first]
        new_rows, dupes, _, _ = ingest_email.ingest(msgs, existing, TODAY)
        self.assertNotIn(first["opportunity_id"], {r["opportunity_id"] for r in new_rows})
        self.assertIn(first["opportunity_id"], {d["opportunity_id"] for d in dupes})

    def test_non_mattress_email_is_rejected(self) -> None:
        msgs = [{
            "id": "reg-1",
            "sender": "TIPS eBid <tips@customer.ionwave.net>",
            "subject": "TIPS eBid System Registration Activation Notification",
            "date": "Tue, 16 Jun 2026 08:00:00 -0500",
            "body": "Dear Supplier, your registration has been activated.",
        }]
        new_rows, _, _, rejected = ingest_email.ingest(msgs, [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(rejected), 1)


class CliTests(unittest.TestCase):
    def _run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ingest_email.main(list(argv))
        return rc, out.getvalue()

    def test_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            active = Path(d) / "active.csv"
            rc, out = self._run("--fixture", str(FIXTURE), "--active", str(active), "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("new:     3", out)
        self.assertFalse(active.exists())

    def test_writes_rows_and_dedups_against_archive(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            active = Path(d) / "active.csv"
            archive = Path(d) / "archive.csv"
            # Seed the archive with the DemandStar opportunity so it is skipped.
            ds = ingest_email.parse_message(_load_fixture()[2], TODAY)
            pipeline.write_rows_atomic(archive, [ds])

            rc, out = self._run("--fixture", str(FIXTURE), "--active", str(active),
                                "--archive", str(archive))
            self.assertEqual(rc, 0)
            self.assertTrue(active.exists())
            _, rows = pipeline.read_rows(active)
            ids = {r["opportunity_id"] for r in rows}
            self.assertNotIn(ds["opportunity_id"], ids)  # deduped via archive
            self.assertEqual(len(rows), 2)  # bonfire + region4 only


class CheckModeTests(unittest.TestCase):
    def test_check_missing_graph_creds_errors_cleanly(self) -> None:
        # With no GRAPH_* env, --check must fail fast (SystemExit) rather
        # than attempting a network call.
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(SystemExit):
                ingest_email.main(["--check", "--provider", "graph"])

    def test_http_hints_cover_common_failures(self) -> None:
        for code in (400, 401, 403, 404):
            self.assertIn(code, ingest_email._HTTP_HINTS)


if __name__ == "__main__":
    unittest.main()
