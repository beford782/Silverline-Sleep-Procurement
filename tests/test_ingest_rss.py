"""Unit tests for tools/ingest_rss.py. Stdlib unittest, no network."""

from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ingest_rss  # noqa: E402
import pipeline  # noqa: E402

RSS = ROOT / "tests" / "fixtures" / "rss_sample.xml"
ATOM = ROOT / "tests" / "fixtures" / "atom_google_alert_sample.xml"
TODAY = "2026-06-17"


def _text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class ParseTests(unittest.TestCase):
    def test_parse_rss(self) -> None:
        entries = ingest_rss.parse_feed(_text(RSS))
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["title"], "Dormitory Mattresses and Bunk Beds")
        self.assertEqual(entries[0]["url"], "https://harriscounty.bonfirehub.com/opportunities/4471")
        self.assertEqual(entries[0]["date"], "2026-06-15")  # RFC-822 -> ISO

    def test_parse_atom(self) -> None:
        entries = ingest_rss.parse_feed(_text(ATOM))
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["date"], "2026-06-17")

    def test_unwrap_google_redirect(self) -> None:
        wrapped = "https://www.google.com/url?rct=j&sa=t&url=https://news.example.com/x&ct=ga"
        self.assertEqual(ingest_rss.unwrap_google_redirect(wrapped), "https://news.example.com/x")

    def test_atom_link_is_unwrapped(self) -> None:
        entries = ingest_rss.parse_feed(_text(ATOM))
        self.assertEqual(entries[0]["url"], "https://news.example.com/university-mattress-rfp")

    def test_parse_garbage_raises(self) -> None:
        with self.assertRaises(ValueError):
            ingest_rss.parse_feed("not xml at all <<<")


class IngestTests(unittest.TestCase):
    def _entries(self, path: Path, source: str):
        return [(e, source) for e in ingest_rss.parse_feed(_text(path))]

    def test_rss_gating(self) -> None:
        new_rows, leads, dupes, rejected = ingest_rss.ingest(
            self._entries(RSS, "Bonfire: Harris County"), [], TODAY)
        active_titles = {r["title"] for r in new_rows}
        lead_titles = {lead["title"]: lead for lead in leads}
        self.assertIn("Dormitory Mattresses and Bunk Beds", active_titles)  # ACCEPT -> active
        # REVIEW broad furniture -> Lead Radar, NOT the active pipeline.
        self.assertNotIn("Office Furniture Catalog (IDIQ)", active_titles)
        self.assertIn("Office Furniture Catalog (IDIQ)", lead_titles)
        office = lead_titles["Office Furniture Catalog (IDIQ)"]
        # "IDIQ" is a co-op vehicle term and outranks the generic furniture cue,
        # so the vehicle-watch signal is preserved.
        self.assertEqual(office["lead_type"], "co-op_contract_vehicle")
        self.assertTrue(office["next_action"].startswith("HUMAN:"))
        self.assertEqual(len(rejected), 1)  # janitorial -> no mattress signal
        self.assertEqual(len(dupes), 0)

    def test_atom_gating_rejects_concrete(self) -> None:
        new_rows, leads, _, rejected = ingest_rss.ingest(self._entries(ATOM, "Google Alerts"), [], TODAY)
        self.assertEqual(len(new_rows), 1)   # university mattress RFP -> active
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(rejected), 1)   # articulated concrete mattress
        self.assertEqual(new_rows[0]["source"], "Google Alerts")

    def test_noise_host_rejected(self) -> None:
        # A Quora result that matched on "bid" must be rejected by host.
        entries = [({
            "title": "Do prisoners get a pillow on their bed in jail?",
            "url": "https://www.quora.com/jail-mattress-question",
            "date": "2026-06-17", "summary": "my pod boss had a comfy 8 year bid jail mattress",
        }, "Google Alerts")]
        new_rows, leads, _, rejected = ingest_rss.ingest(entries, [], TODAY)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 0)
        self.assertEqual(len(rejected), 1)
        self.assertIn("host", rejected[0]["next_action"])

    def test_retail_catalog_without_cue_is_lead(self) -> None:
        # Competitor product page: mattress term, no procurement cue -> REVIEW
        # -> Lead Radar (not active).
        entries = [({
            "title": "Clear Advantage Jail Mattress",
            "url": "https://hardtimeproducts.com/jail-mattress",
            "date": "2026-06-17", "summary": "Cortech EZ Bunk Clear Advantage Jail Mattress $104.99",
        }, "Google Alerts")]
        new_rows, leads, _, rejected = ingest_rss.ingest(entries, [], TODAY)
        self.assertEqual(len(rejected), 0)
        self.assertEqual(len(new_rows), 0)
        self.assertEqual(len(leads), 1)
        self.assertTrue(leads[0]["next_action"].startswith("HUMAN:"))

    def test_dedup_against_existing(self) -> None:
        entries = self._entries(RSS, "Bonfire: Harris County")
        first = ingest_rss.entry_to_row(entries[0][0], "Bonfire: Harris County", TODAY)
        new_rows, _leads, dupes, _ = ingest_rss.ingest(entries, [first], TODAY)
        self.assertIn(first["opportunity_id"], {d["opportunity_id"] for d in dupes})
        self.assertNotIn(first["opportunity_id"], {r["opportunity_id"] for r in new_rows})


class CliTests(unittest.TestCase):
    def test_fixture_dry_run(self) -> None:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = ingest_rss.main(["--fixture", str(RSS), "--source", "Bonfire", "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("rejected: 1", out.getvalue())
        self.assertIn("leads:    1", out.getvalue())  # office furniture -> Lead Radar

    def test_fixture_writes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            active = Path(d) / "active.csv"
            rc = ingest_rss.main(["--fixture", str(ATOM), "--source", "Google Alerts",
                                  "--active", str(active)])
            self.assertEqual(rc, 0)
            _, rows = pipeline.read_rows(active)
            self.assertEqual(len(rows), 1)  # only the mattress RFP, concrete rejected

    def test_fixture_writes_leads_not_active(self) -> None:
        # The RSS sample's broad furniture item must land in Lead Radar while
        # the active pipeline gets only the explicit mattress row.
        with tempfile.TemporaryDirectory() as d:
            active = Path(d) / "active.csv"
            leads = Path(d) / "leads.csv"
            rc = ingest_rss.main(["--fixture", str(RSS), "--source", "Bonfire: Harris County",
                                  "--active", str(active), "--leads", str(leads)])
            self.assertEqual(rc, 0)
            _, active_rows = pipeline.read_rows(active)
            self.assertEqual(len(active_rows), 1)  # dormitory mattresses only
            self.assertEqual(active_rows[0]["title"], "Dormitory Mattresses and Bunk Beds")
            _, lead_rows = ingest_rss.lead_radar.read_lead_rows(leads)
            self.assertEqual(len(lead_rows), 1)    # office furniture catalog (IDIQ)
            self.assertEqual(lead_rows[0]["lead_type"], "co-op_contract_vehicle")


if __name__ == "__main__":
    unittest.main()
