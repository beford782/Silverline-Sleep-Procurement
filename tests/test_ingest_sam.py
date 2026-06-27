"""Unit tests for tools/ingest_sam.py. Stdlib unittest, no live API calls."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
FIXTURE = ROOT / "tests" / "fixtures" / "sam_response.json"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ingest_sam  # noqa: E402
import pipeline  # noqa: E402


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class RecordMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        with FIXTURE.open("r", encoding="utf-8") as fh:
            self.payload = json.load(fh)
        self.records = self.payload["opportunitiesData"]

    def test_record_to_row_maps_documented_fields(self) -> None:
        row = ingest_sam.record_to_row(self.records[0], today="2026-05-14")
        self.assertEqual(row["source"], "SAM.gov")
        self.assertEqual(row["solicitation_number"], "15B30025R00000001")
        self.assertEqual(row["title"], self.records[0]["title"])
        self.assertIn("DEPT OF JUSTICE", row["buyer"])
        self.assertIn("FEDERAL BUREAU OF PRISONS", row["buyer"])
        self.assertEqual(row["status"], "watching")
        self.assertEqual(row["posted_date"], "2026-05-08")
        # Due date is normalized from ISO+timezone to plain YYYY-MM-DD.
        self.assertEqual(row["due_date"], "2026-06-15")
        self.assertEqual(row["delivery_location"], "Houston, TX")
        self.assertIn("NAICS 337910", row["commodity_terms"])
        self.assertIn("PSC 7105", row["commodity_terms"])
        self.assertEqual(row["portal_url"], "https://sam.gov/opp/synthetic-notice-aaa111/view")
        self.assertEqual(row["created_date"], "2026-05-14")
        self.assertEqual(row["last_reviewed"], "2026-05-14")
        self.assertEqual(row["notes"], "Solicitation")
        self.assertEqual(row["procurement_risk"], "blocker")
        self.assertEqual(row["gate_status"], "blocked")
        self.assertEqual(row["compliance_blocker"], "sam_registration_pending; specs_pending")
        # opportunity_id is slugified and stable
        self.assertEqual(
            row["opportunity_id"],
            "sam-gov-dept-of-justice-federal-bureau-of-prisons-15b30025r00000001",
        )
        # No PII fields leaked into the row.
        for k, v in row.items():
            self.assertNotIn("@", v, f"unexpected email-like content in {k!r}: {v!r}")

    def test_record_to_row_handles_missing_optional_fields(self) -> None:
        sparse = {
            "noticeId": "spare-001",
            "title": "Bed frames",
            "fullParentPathName": "AGENCY",
            "postedDate": "2026-05-09",
            # no responseDeadLine, no naicsCode, no placeOfPerformance, no uiLink
        }
        row = ingest_sam.record_to_row(sparse, today="2026-05-14")
        self.assertEqual(row["solicitation_number"], "")
        self.assertEqual(row["due_date"], "")
        self.assertEqual(row["delivery_location"], "")
        self.assertEqual(row["commodity_terms"], "")
        self.assertEqual(row["portal_url"], "")
        # opportunity_id falls back to noticeId when solicitationNumber missing.
        self.assertEqual(row["opportunity_id"], "sam-gov-agency-spare-001")

    def test_ingest_dedupes_against_existing_solicitation_numbers(self) -> None:
        existing = [
            {k: "" for k in pipeline.CANONICAL_HEADER}
            | {
                "opportunity_id": "some-other-id",
                "solicitation_number": "15B30025R00000001",  # collides with fixture row 1
                "source": "SAM.gov",
                "buyer": "DEPT OF JUSTICE",
                "title": "previously ingested",
                "status": "watching",
            }
        ]
        new_rows, dupes, _ = ingest_sam.ingest(self.records, existing, today="2026-05-14")
        self.assertEqual(len(new_rows), 2)
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0]["solicitation_number"], "15B30025R00000001")

    def test_ingest_dedupes_against_existing_opportunity_ids(self) -> None:
        first_row = ingest_sam.record_to_row(self.records[0], today="2026-05-14")
        existing = [first_row]
        new_rows, dupes, _ = ingest_sam.ingest(self.records, existing, today="2026-05-14")
        self.assertEqual(len(new_rows), 2)
        self.assertEqual(len(dupes), 1)


class SearchUrlTests(unittest.TestCase):
    def test_search_url_includes_required_params(self) -> None:
        url = ingest_sam.build_search_url(
            api_key="TESTKEY",
            posted_from="2026-05-01",
            posted_to="2026-05-14",
            title="mattress",
            limit=50,
            offset=0,
            naics_code="337910",
            notice_type="o",
        )
        self.assertIn("api_key=TESTKEY", url)
        # SAM.gov expects MM/dd/yyyy in the query string.
        self.assertIn("postedFrom=05%2F01%2F2026", url)
        self.assertIn("postedTo=05%2F14%2F2026", url)
        # `title` is the documented parameter (not the made-up `q`).
        self.assertIn("title=mattress", url)
        self.assertNotIn("q=mattress", url)
        # NAICS code goes as `ncode`, notice type as `ptype` per docs.
        self.assertIn("ncode=337910", url)
        self.assertIn("ptype=o", url)
        self.assertIn("limit=50", url)
        self.assertIn("offset=0", url)

    def test_search_url_omits_unused_optional_params(self) -> None:
        url = ingest_sam.build_search_url(
            api_key="K",
            posted_from="2026-05-01",
            posted_to="2026-05-14",
        )
        self.assertNotIn("title=", url)
        self.assertNotIn("q=", url)
        self.assertNotIn("ncode=", url)
        self.assertNotIn("ccode=", url)
        self.assertNotIn("ptype=", url)
        self.assertNotIn("rdlfrom=", url)
        self.assertNotIn("rdlto=", url)

    def test_search_url_includes_psc_classification_code(self) -> None:
        # PSC sweeps (e.g. 7210 household furnishings, 7105 furniture) catch
        # bedding/furniture solicitations whose titles never say "mattress".
        url = ingest_sam.build_search_url(
            api_key="K",
            posted_from="2026-05-01",
            posted_to="2026-05-14",
            classification_code="7210",
        )
        # PSC goes as `ccode` on the request side per the SAM.gov v2 docs.
        self.assertIn("ccode=7210", url)

    def test_search_url_includes_response_deadline_filters(self) -> None:
        url = ingest_sam.build_search_url(
            api_key="K",
            posted_from="2026-01-01",
            posted_to="2026-05-14",
            response_deadline_after="2026-05-15",
            response_deadline_before="2026-12-31",
        )
        # Same MM/dd/yyyy encoding as postedFrom/postedTo.
        self.assertIn("rdlfrom=05%2F15%2F2026", url)
        self.assertIn("rdlto=12%2F31%2F2026", url)


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.archive = self.tmp / "archive.csv"
        # Header-only starting state for both files.
        for path in (self.active, self.archive):
            with path.open("w", encoding="utf-8", newline="") as fh:
                fh.write(",".join(pipeline.CANONICAL_HEADER) + "\n")

    def _seed_archive_with_first_fixture_row(self) -> dict:
        """Write the first fixture row into the archive CSV as a closed no-bid."""
        with FIXTURE.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        first_record = payload["opportunitiesData"][0]
        archive_row = ingest_sam.record_to_row(first_record, today="2026-05-14")
        archive_row["status"] = "no-bid"
        archive_row["next_action"] = "No-bid archived"
        archive_row["last_reviewed"] = "2026-05-15"
        with self.archive.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
            writer.writeheader()
            writer.writerow({k: archive_row.get(k, "") for k in pipeline.CANONICAL_HEADER})
        return archive_row

    def _run(self, *argv: str, env: dict | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        original_env = dict(os.environ)
        if env is not None:
            os.environ.clear()
            os.environ.update(env)
        rc = -1
        try:
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = ingest_sam.main(list(argv))
                except SystemExit as exc:
                    rc = int(exc.code) if exc.code is not None else 0
        finally:
            os.environ.clear()
            os.environ.update(original_env)
        return rc, out.getvalue(), err.getvalue()

    def test_dry_run_with_fixture_does_not_write(self) -> None:
        rc, out, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--dry-run",
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("fetched: 3", out)
        self.assertIn("new:    3", out)
        self.assertIn("--dry-run", out)
        rows = _read_csv(self.active)
        self.assertEqual(rows, [])  # nothing written

    def test_fixture_write_appends_rows_and_dedupes(self) -> None:
        rc, out, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
        )
        self.assertEqual(rc, 0, err)
        rows = _read_csv(self.active)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["source"] == "SAM.gov" for r in rows))

        # Re-running the same fixture should add zero new rows.
        rc2, out2, err2 = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
        )
        self.assertEqual(rc2, 0, err2)
        self.assertIn("dupes:  3", out2)
        rows_after = _read_csv(self.active)
        self.assertEqual(len(rows_after), 3)

    def test_missing_api_key_errors_when_not_using_fixture(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "SAM_API_KEY"}
        rc, _, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--active", str(self.active),
            "--dry-run",
            env=env,
        )
        self.assertEqual(rc, 2)
        self.assertIn("SAM_API_KEY", err)

    def test_invalid_date_format_rejected(self) -> None:
        rc, _, err = self._run(
            "--posted-from", "yesterday",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--dry-run",
        )
        self.assertEqual(rc, 2)
        self.assertIn("YYYY-MM-DD", err)

    def test_fetch_page_uses_urlopen(self) -> None:
        # Confirm fetch_page is wired through urllib.request.urlopen; CI
        # never hits the live API but the wiring must be in place.
        payload = {"opportunitiesData": [], "totalRecords": 0, "limit": 50, "offset": 0}
        body = json.dumps(payload).encode("utf-8")
        fake_resp = mock.MagicMock()
        fake_resp.__enter__.return_value = fake_resp
        fake_resp.read.return_value = body
        with mock.patch("urllib.request.urlopen", return_value=fake_resp) as mocked:
            out = ingest_sam.fetch_page("https://api.sam.gov/opportunities/v2/search?api_key=x")
        mocked.assert_called_once()
        self.assertEqual(out, payload)

    def test_default_response_deadline_after_is_today(self) -> None:
        # Without --response-deadline-after or --include-past-due, the
        # ingester should send rdlfrom=today so past-due opportunities are
        # excluded. Capture the URL passed to fetch_page.
        captured: dict[str, str] = {}

        def fake_fetch_page(url, timeout=30):
            captured["url"] = url
            return {"opportunitiesData": [], "totalRecords": 0, "limit": 50, "offset": 0}

        with mock.patch.object(ingest_sam, "fetch_page", side_effect=fake_fetch_page), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, _, err = self._run(
                "--posted-from", "2026-04-14",
                "--posted-to", "2026-05-14",
                "--active", str(self.active),
                "--dry-run",
            )
        self.assertEqual(rc, 0, err)
        self.assertIn("url", captured)
        self.assertIn("rdlfrom=", captured["url"])

    def test_include_past_due_skips_default_rdlfrom(self) -> None:
        captured: dict[str, str] = {}

        def fake_fetch_page(url, timeout=30):
            captured["url"] = url
            return {"opportunitiesData": [], "totalRecords": 0, "limit": 50, "offset": 0}

        with mock.patch.object(ingest_sam, "fetch_page", side_effect=fake_fetch_page), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, _, err = self._run(
                "--posted-from", "2026-04-14",
                "--posted-to", "2026-05-14",
                "--include-past-due",
                "--active", str(self.active),
                "--dry-run",
            )
        self.assertEqual(rc, 0, err)
        self.assertNotIn("rdlfrom=", captured["url"])

    def test_explicit_response_deadline_after_wins_over_include_past_due(self) -> None:
        captured: dict[str, str] = {}

        def fake_fetch_page(url, timeout=30):
            captured["url"] = url
            return {"opportunitiesData": [], "totalRecords": 0, "limit": 50, "offset": 0}

        with mock.patch.object(ingest_sam, "fetch_page", side_effect=fake_fetch_page), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, _, _ = self._run(
                "--posted-from", "2026-04-14",
                "--posted-to", "2026-05-14",
                "--response-deadline-after", "2026-06-01",
                "--include-past-due",  # ignored because explicit flag wins
                "--active", str(self.active),
                "--dry-run",
            )
        self.assertEqual(rc, 0)
        self.assertIn("rdlfrom=06%2F01%2F2026", captured["url"])

    def test_archive_row_is_reported_as_dupe_and_not_written_to_active(self) -> None:
        archived = self._seed_archive_with_first_fixture_row()
        rc, out, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        # Fixture has 3 records; one matches the archived row, so 2 new + 1 dupe.
        self.assertIn("fetched: 3", out)
        self.assertIn("new:    2", out)
        self.assertIn("dupes:  1 (0 active, 1 archive)", out)

        # Active must contain only the 2 non-archived records — the archived
        # row must NOT have been echoed back into active.
        active_rows = _read_csv(self.active)
        self.assertEqual(len(active_rows), 2)
        active_ids = {r["opportunity_id"] for r in active_rows}
        self.assertNotIn(archived["opportunity_id"], active_ids)

        # Archive must remain untouched (still just the one seeded row).
        archive_rows = _read_csv(self.archive)
        self.assertEqual(len(archive_rows), 1)
        self.assertEqual(archive_rows[0]["opportunity_id"], archived["opportunity_id"])
        self.assertEqual(archive_rows[0]["status"], "no-bid")

    def test_archive_dedupe_with_solicitation_number_only(self) -> None:
        # Archive entry shares only the solicitation_number with the fixture
        # record — dedup must still catch it even when opportunity_id differs.
        with self.archive.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
            writer.writeheader()
            row = {k: "" for k in pipeline.CANONICAL_HEADER}
            row.update({
                "opportunity_id": "manual-tracking-id-not-from-sam",
                "source": "SAM.gov",
                "buyer": "DEPT OF JUSTICE",
                "solicitation_number": "15B30025R00000001",  # fixture row 1
                "title": "previously closed",
                "status": "no-bid",
            })
            writer.writerow(row)

        rc, out, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("dupes:  1 (0 active, 1 archive)", out)
        active_rows = _read_csv(self.active)
        self.assertEqual(len(active_rows), 2)
        self.assertNotIn(
            "15B30025R00000001",
            {r["solicitation_number"] for r in active_rows},
        )

    def test_missing_archive_file_treated_as_empty(self) -> None:
        # --archive pointing at a non-existent file should not error; ingest
        # should fall back to active-only dedup.
        missing = self.tmp / "does_not_exist.csv"
        self.assertFalse(missing.exists())
        rc, out, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--archive", str(missing),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("new:    3", out)
        self.assertIn("dupes:  0 (0 active, 0 archive)", out)
        self.assertEqual(len(_read_csv(self.active)), 3)

    def test_active_and_archive_dupes_break_out_separately(self) -> None:
        # First run: write all 3 fixture records to active.
        rc, _, err = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        # Now move row 1 into the archive manually (simulates close-and-archive).
        active_rows = _read_csv(self.active)
        moved = next(r for r in active_rows if r["solicitation_number"] == "15B30025R00000001")
        remaining = [r for r in active_rows if r["solicitation_number"] != "15B30025R00000001"]
        with self.active.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
            writer.writeheader()
            writer.writerows(remaining)
        with self.archive.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
            writer.writeheader()
            moved["status"] = "no-bid"
            writer.writerow(moved)

        # Second run: 2 active dupes + 1 archive dupe expected.
        rc2, out2, err2 = self._run(
            "--posted-from", "2026-05-01",
            "--posted-to", "2026-05-14",
            "--fixture", str(FIXTURE),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc2, 0, err2)
        self.assertIn("dupes:  3 (2 active, 1 archive)", out2)
        self.assertEqual(len(_read_csv(self.active)), 2)

    def test_http_404_is_treated_as_zero_results(self) -> None:
        # SAM.gov returns 404 when no opportunities match the query, per
        # their docs. The script must treat that as a normal empty
        # result, exit 0, and not write anything.
        import urllib.error

        def raise_404(*_a, **_kw):
            raise urllib.error.HTTPError(
                url="https://api.sam.gov/opportunities/v2/search",
                code=404,
                msg="No Data found",
                hdrs=None,
                fp=io.BytesIO(b""),
            )

        with mock.patch("urllib.request.urlopen", side_effect=raise_404), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, out, err = self._run(
                "--posted-from", "2026-05-01",
                "--posted-to", "2026-05-14",
                "--title", "no-match-keyword",
                "--active", str(self.active),
            )
        self.assertEqual(rc, 0, err)
        self.assertIn("fetched: 0", out)
        self.assertIn("no new rows", out)
        # No rows should have landed in the pipeline.
        rows = _read_csv(self.active)
        self.assertEqual(rows, [])

    def test_http_429_errors_by_default(self) -> None:
        import urllib.error

        def raise_429(*_a, **_kw):
            raise urllib.error.HTTPError(
                url="https://api.sam.gov/opportunities/v2/search",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=io.BytesIO(b'{"code":"900804","message":"Message throttled out"}'),
            )

        with mock.patch("urllib.request.urlopen", side_effect=raise_429), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, _, err = self._run(
                "--posted-from", "2026-05-01",
                "--posted-to", "2026-05-14",
                "--title", "mattress",
                "--active", str(self.active),
            )
        self.assertEqual(rc, 1)
        self.assertIn("HTTP 429", err)
        self.assertEqual(_read_csv(self.active), [])

    def test_http_429_can_be_treated_as_empty_for_scheduled_runs(self) -> None:
        import urllib.error

        def raise_429(*_a, **_kw):
            raise urllib.error.HTTPError(
                url="https://api.sam.gov/opportunities/v2/search",
                code=429,
                msg="Too Many Requests",
                hdrs=None,
                fp=io.BytesIO(b'{"code":"900804","message":"Message throttled out"}'),
            )

        with mock.patch("urllib.request.urlopen", side_effect=raise_429), \
             mock.patch.dict(os.environ, {"SAM_API_KEY": "fakekey"}, clear=False):
            rc, out, err = self._run(
                "--posted-from", "2026-05-01",
                "--posted-to", "2026-05-14",
                "--title", "mattress",
                "--active", str(self.active),
                "--allow-throttled-empty",
            )
        self.assertEqual(rc, 0, err)
        self.assertIn("HTTP 429", err)
        self.assertIn("fetched: 0", out)
        self.assertIn("no new rows", out)
        self.assertEqual(_read_csv(self.active), [])


if __name__ == "__main__":
    unittest.main()
