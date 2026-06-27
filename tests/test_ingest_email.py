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
        self.assertEqual(row["procurement_risk"], "medium")
        self.assertEqual(row["gate_status"], "triage")
        self.assertEqual(row["compliance_blocker"], "portal_verification_pending; specs_pending")
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
        new_rows, leads, dupes, skipped, rejected = ingest_email.ingest(_load_fixture(), [], TODAY)
        self.assertEqual(len(new_rows), 3)   # bonfire, region4, demandstar (all mattress)
        self.assertEqual(len(leads), 0)      # no broad/review items in this fixture
        self.assertEqual(len(dupes), 1)      # bonfire duplicate
        self.assertEqual(len(skipped), 1)    # empty subject
        self.assertEqual(len(rejected), 0)   # all fixture items are mattress-relevant

    def test_dedup_against_existing(self) -> None:
        msgs = _load_fixture()
        first = ingest_email.parse_message(msgs[0], TODAY)
        existing = [first]
        new_rows, _leads, dupes, _, _ = ingest_email.ingest(msgs, existing, TODAY)
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
        new_rows, leads, _, _, rejected = ingest_email.ingest(msgs, [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(rejected), 1)

    def test_dormitory_mattress_routes_to_active_not_leads(self) -> None:
        # An explicit mattress item is a confirmed product-fit -> active pipeline.
        bonfire = _load_fixture()[0]
        new_rows, leads, _, _, _ = ingest_email.ingest([bonfire], [], TODAY)
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(len(leads), 0)
        self.assertEqual(new_rows[0]["title"], "Dormitory Mattresses and Bed Frames")

    def test_broad_furniture_routes_to_leads_not_active(self) -> None:
        # A broad IonWave furniture/related-services digest is REVIEW-band:
        # it must feed Lead Radar, never the strict active pipeline.
        digest = IonWaveDigestTests.DIGEST
        new_rows, leads, _, _, _ = ingest_email.ingest([digest], [], TODAY)
        self.assertEqual(len(new_rows), 0)  # nothing pollutes active bids
        self.assertEqual(len(leads), 2)     # both furniture bids land as leads
        titles = {lead["title"] for lead in leads}
        self.assertIn("School Furniture & Related Services", titles)
        for lead in leads:
            self.assertEqual(lead["lead_type"], "broad_furniture_ffe")
            self.assertEqual(lead["status"], "reviewing")
            self.assertTrue(lead["next_action"].startswith("HUMAN:"))
            self.assertTrue(lead["lead_id"])
            self.assertTrue(set(lead).issuperset(set(ingest_email.lead_radar.LEAD_HEADER)))

    def test_review_target_active_keeps_legacy_behavior(self) -> None:
        # Opt back into the old behavior: REVIEW items go to active, flagged.
        digest = IonWaveDigestTests.DIGEST
        new_rows, leads, _, _, _ = ingest_email.ingest(
            [digest], [], TODAY, review_target="active")
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(new_rows), 2)
        self.assertTrue(all(r["next_action"].startswith("HUMAN:") for r in new_rows))


class IonWaveDigestTests(unittest.TestCase):
    # A real-shape ESC eMarketplace "Matching Bid Opportunities" alert that
    # bundles two solicitations as labeled blocks (label-then-value on its own
    # line, as Gmail plaintext renders it).
    DIGEST = {
        "id": "gmail-ionwave-1",
        "sender": "ESC 6 eMarketplace <esc6emkt@customer.ionwave.net>",
        "subject": "ESC 6 eMarketplace Matching Bid Opportunities",
        "date": "Wed, 13 May 2026 09:50:00 -0500",
        "body": (
            "Dear Supplier,\n"
            "Bid Number:\nRFP 15.26\n"
            "Title:\nOffice - Supplies, Equipment, Furniture & Services\n"
            "Description:\nEPIC6 seeks proposals for office supplies.\n"
            "Open Date:\n5/1/2026 08:00:02 AM (CT)\n"
            "Close Date:\n6/5/2026 03:00:00 PM (CT)\n"
            "Question Cut Off Date:\n5/28/2026 03:00:00 PM (CT)\n"
            "Bid Number:\nRFP 16.26\n"
            "Title:\nSchool Furniture & Related Services\n"
            "Description:\nEPIC6 seeks proposals for school furniture.\n"
            "Open Date:\n5/1/2026 08:00:01 AM (CT)\n"
            "Close Date:\n6/5/2026 03:00:00 PM (CT)\n"
            "The agency can be accessed at: https://esc6emkt.ionwave.net/\n"
        ),
    }

    def test_split_yields_one_submessage_per_bid(self) -> None:
        subs = ingest_email.split_ionwave_digest(self.DIGEST)
        self.assertIsNotNone(subs)
        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["subject"], "Office - Supplies, Equipment, Furniture & Services")
        self.assertEqual(subs[0]["solicitation_number"], "RFP 15.26")
        self.assertEqual(subs[1]["subject"], "School Furniture & Related Services")
        self.assertEqual(subs[1]["solicitation_number"], "RFP 16.26")

    def test_non_ionwave_sender_not_split(self) -> None:
        msg = dict(self.DIGEST, sender="notifications@gobonfire.com")
        self.assertIsNone(ingest_email.split_ionwave_digest(msg))

    def test_ionwave_without_bid_blocks_not_split(self) -> None:
        # The Region 4 (ionwave.net) sample has no "Bid Number:/Title:" blocks.
        msg = {
            "id": "x", "sender": "noreply@region4esc.ionwave.net",
            "subject": "Bid Invitation: Mattresses", "date": "",
            "body": "Response due 07/10/2026. https://region4esc.ionwave.net/x",
        }
        self.assertIsNone(ingest_email.split_ionwave_digest(msg))

    def test_digest_ingests_as_two_leads_with_fields(self) -> None:
        # Broad furniture digest -> Lead Radar (not active), one lead per bid,
        # fields carried through including the "Close Date:" due_date fix.
        new_rows, leads, _, _, _ = ingest_email.ingest([self.DIGEST], [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 2)
        by_soln = {lead["solicitation_number"]: lead for lead in leads}
        self.assertEqual(by_soln["RFP 16.26"]["title"], "School Furniture & Related Services")
        self.assertEqual(by_soln["RFP 16.26"]["due_date"], "2026-06-05")
        self.assertEqual(by_soln["RFP 16.26"]["source"], "IonWave")

    def test_bid_title_issue_date_variant(self) -> None:
        # The "question answered" variant uses "Bid Title:" / "Issue Date:".
        msg = {
            "id": "qa-1",
            "sender": "esc6emkt@customer.ionwave.net",
            "subject": "ESC 6 eMarketplace Bid Question Answered: RFP 16.26",
            "date": "Tue, 26 May 2026 14:44:00 -0500",
            "body": (
                "Bid Number:\nRFP 16.26\n"
                "Bid Title:\nSchool Furniture & Related Services\n"
                "Issue Date:\n5/1/2026 08:00:01 AM (CT)\n"
                "Close Date:\n6/5/2026 03:00:00 PM (CT)\n"
            ),
        }
        subs = ingest_email.split_ionwave_digest(msg)
        self.assertEqual(len(subs), 1)
        self.assertEqual(subs[0]["subject"], "School Furniture & Related Services")
        self.assertEqual(subs[0]["solicitation_number"], "RFP 16.26")

    def test_digest_and_question_alert_dedupe_by_solicitation_number(self) -> None:
        # A later "question answered" alert for the same bid has different
        # body/url text, but should not create a second active pipeline row.
        qa = {
            "id": "qa-1",
            "sender": "esc6emkt@customer.ionwave.net",
            "subject": "ESC 6 eMarketplace Bid Question Answered: RFP 16.26",
            "date": "Tue, 26 May 2026 14:44:00 -0500",
            "body": (
                "Bid Number:\nRFP 16.26\n"
                "Bid Title:\nSchool Furniture & Related Services\n"
                "Issue Date:\n5/1/2026 08:00:01 AM (CT)\n"
                "Close Date:\n6/5/2026 03:00:00 PM (CT)\n"
                "https://esc6emkt.ionwave.net/VendorLanding.aspx?e=question"
            ),
        }
        new_rows, leads, dupes, _, _ = ingest_email.ingest([self.DIGEST, qa], [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 2)
        self.assertEqual(len(dupes), 1)
        self.assertEqual(dupes[0]["solicitation_number"], "RFP 16.26")

    def test_close_date_label_now_extracts(self) -> None:
        # Regression for the DUE_DATE_RE "Close Date:" fix.
        self.assertEqual(
            ingest_email.extract_due_date("Close Date: 6/5/2026 03:00:00 PM (CT)"),
            "2026-06-05",
        )


FORWARDED_FIXTURE = ROOT / "tests" / "fixtures" / "email_alerts_forwarded_sample.json"


class ForwardedAlertTests(unittest.TestCase):
    """Outlook-forwarded alerts must parse like direct ones on every provider
    path (the scheduled weekly run reads forwarded items via Microsoft Graph)."""

    def _load(self) -> list[dict]:
        with FORWARDED_FIXTURE.open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_unwrap_recovers_original_sender_and_subject(self) -> None:
        msg = self._load()[0]  # forwarded IonWave digest
        self.assertIn("silverlinesleep.com", msg["sender"])  # forwarding mailbox
        out = ingest_email.unwrap_forwarded(msg)
        self.assertEqual(out["sender"], "ESC 6 eMarketplace <esc6emkt@customer.ionwave.net>")
        self.assertEqual(out["subject"], "ESC 6 eMarketplace Matching Bid Opportunities")
        # Source now maps to the real portal, not the forwarder's domain.
        self.assertEqual(ingest_email.source_for_sender(out["sender"]), "IonWave")
        # Body trimmed to the forwarded content (signature preamble dropped).
        self.assertTrue(out["body"].lstrip().startswith("From: ESC 6 eMarketplace"))
        # Original message date is preserved (it parses; the quoted "Sent:" does not).
        self.assertEqual(out["date"], msg["date"])

    def test_unwrap_is_noop_on_direct_alert(self) -> None:
        # A normal direct alert (no forwarded header block) is returned unchanged.
        direct = _load_fixture()[0]  # Bonfire direct alert
        self.assertIs(ingest_email.unwrap_forwarded(direct), direct)

    def test_forwarded_digest_routes_to_lead_radar(self) -> None:
        digest = self._load()[0]
        new_rows, leads, _, _, _ = ingest_email.ingest([digest], [], TODAY)
        self.assertEqual(len(new_rows), 0)  # broad furniture never hits active
        self.assertEqual(len(leads), 2)
        by_soln = {lead["solicitation_number"]: lead for lead in leads}
        self.assertEqual(set(by_soln), {"RFP 15.26", "RFP 16.26"})
        self.assertEqual(by_soln["RFP 16.26"]["title"], "School Furniture & Related Services")
        self.assertEqual(by_soln["RFP 16.26"]["source"], "IonWave")
        self.assertEqual(by_soln["RFP 16.26"]["due_date"], "2026-06-05")

    def test_forwarded_mattress_routes_to_active(self) -> None:
        mattress = self._load()[1]
        new_rows, leads, _, _, _ = ingest_email.ingest([mattress], [], TODAY)
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(new_rows[0]["source"], "Bonfire")
        self.assertEqual(new_rows[0]["title"], "Dormitory Mattresses and Bed Frames")
        self.assertEqual(new_rows[0]["portal_url"],
                         "https://city.bonfirehub.com/opportunities/55501")

    def test_forwarded_registration_is_rejected(self) -> None:
        reg = self._load()[2]
        new_rows, leads, _, _, rejected = ingest_email.ingest([reg], [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(rejected), 1)

    def test_whole_forwarded_fixture_routing(self) -> None:
        new_rows, leads, dupes, skipped, rejected = ingest_email.ingest(self._load(), [], TODAY)
        self.assertEqual(len(new_rows), 1)   # forwarded Bonfire mattress -> active
        self.assertEqual(len(leads), 2)      # forwarded ESC6 furniture digest -> Lead Radar
        self.assertEqual(len(rejected), 1)   # forwarded TIPS registration notice
        self.assertEqual(len(dupes), 0)
        self.assertEqual(len(skipped), 0)

    def test_forwarded_via_graph_provider_path(self) -> None:
        # Mirror the scheduled run: a Microsoft Graph message whose own sender is
        # the forwarding mailbox, carrying a forwarded IonWave digest in a text
        # body (Graph is fetched with Prefer: outlook.body-content-type="text").
        graph_msg = {
            "id": "AAMk-fwd-1",
            "subject": "FW: ESC 6 eMarketplace Matching Bid Opportunities",
            "from": {"emailAddress": {"name": "Blake Ford", "address": "beford@silverlinesleep.com"}},
            "receivedDateTime": "2026-05-13T14:55:00Z",
            "body": {"contentType": "text", "content": self._load()[0]["body"]},
        }
        norm = ingest_email.normalize_graph_message(graph_msg)
        self.assertEqual(norm["sender"], "beford@silverlinesleep.com")  # forwarder
        new_rows, leads, _, _, _ = ingest_email.ingest([norm], [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 2)
        self.assertEqual({lead["source"] for lead in leads}, {"IonWave"})
        self.assertEqual({lead["solicitation_number"] for lead in leads},
                         {"RFP 15.26", "RFP 16.26"})


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
        self.assertIn("active:  3", out)
        self.assertFalse(active.exists())

    def test_broad_digest_writes_leads_not_active(self) -> None:
        # End-to-end: a furniture digest fixture must write Lead Radar rows and
        # leave the active pipeline untouched (0 rows).
        with tempfile.TemporaryDirectory() as d:
            active = Path(d) / "active.csv"
            leads = Path(d) / "leads.csv"
            digest_fixture = Path(d) / "digest.json"
            digest_fixture.write_text(json.dumps([IonWaveDigestTests.DIGEST]), encoding="utf-8")
            rc, out = self._run("--fixture", str(digest_fixture), "--active", str(active),
                                "--leads", str(leads))
            self.assertEqual(rc, 0)
            self.assertFalse(active.exists())  # active pipeline never written
            self.assertTrue(leads.exists())
            _, lead_rows = ingest_email.lead_radar.read_lead_rows(leads)
            self.assertEqual(len(lead_rows), 2)
            self.assertIn("leads:   2", out)

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


class ImapProviderTests(unittest.TestCase):
    """The IMAP provider (Gmail app-password path) must produce the same
    normalized message dicts as Graph/Gmail so the parser chain is unchanged."""

    def _raw(self, *, subject: str, sender: str, plain: str = "", html: str = "",
             msgid: str = "<m1@mail>", date: str = "Mon, 15 Jun 2026 09:00:00 -0500") -> bytes:
        import email.message
        m = email.message.EmailMessage()
        m["Message-ID"] = msgid
        m["From"] = sender
        m["Subject"] = subject
        m["Date"] = date
        if plain:
            m.set_content(plain)
        if html:
            if plain:
                m.add_alternative(html, subtype="html")
            else:
                m.set_content(html, subtype="html")
        return bytes(m)

    def test_normalize_maps_canonical_fields(self) -> None:
        raw = self._raw(
            subject="New Opportunity: Dormitory Mattresses",
            sender="City Purchasing <notifications@gobonfire.com>",
            plain="Project: Dormitory Mattresses\nView: https://city.bonfirehub.com/opportunities/5\n",
        )
        out = ingest_email.normalize_imap_message(raw)
        self.assertEqual(out["id"], "<m1@mail>")
        self.assertEqual(out["sender"], "City Purchasing <notifications@gobonfire.com>")
        self.assertEqual(out["subject"], "New Opportunity: Dormitory Mattresses")
        self.assertIn("2026", out["date"])
        self.assertIn("Dormitory Mattresses", out["body"])

    def test_normalize_decodes_rfc2047_subject(self) -> None:
        raw = self._raw(
            subject="=?UTF-8?Q?Correctional_Mattresses_=E2=80=94_RFB?=",
            sender="bids@example.gov",
            plain="See attached.",
        )
        out = ingest_email.normalize_imap_message(raw)
        self.assertEqual(out["subject"], "Correctional Mattresses — RFB")

    def test_normalize_prefers_plain_over_html(self) -> None:
        raw = self._raw(
            subject="Bid",
            sender="a@b.com",
            plain="PLAIN BODY mattress",
            html="<p>HTML BODY mattress</p>",
        )
        out = ingest_email.normalize_imap_message(raw)
        self.assertIn("PLAIN BODY", out["body"])
        self.assertNotIn("<p>", out["body"])

    def test_normalize_html_only_is_stripped(self) -> None:
        raw = self._raw(
            subject="Bid",
            sender="a@b.com",
            html="<html><body><p>Inmate <b>mattress</b> RFQ</p></body></html>",
        )
        out = ingest_email.normalize_imap_message(raw)
        self.assertIn("mattress", out["body"])
        self.assertNotIn("<b>", out["body"])

    def test_normalized_imap_message_feeds_relevance_chain(self) -> None:
        raw = self._raw(
            subject="Invitation for Bid: Correctional Mattresses",
            sender="City Purchasing <notifications@gobonfire.com>",
            plain="Jail mattresses for the county detention center. View the opportunity online.",
        )
        msg = ingest_email.normalize_imap_message(raw)
        new_rows, _leads, _dupes, _skipped, _rejected = ingest_email.ingest([msg], [], TODAY)
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(new_rows[0]["source"], "Bonfire")


if __name__ == "__main__":
    unittest.main()
