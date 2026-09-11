"""Active-scope gate: an ACCEPT-graded SAM notice with a foreign place of
performance or a non-mattress NAICS goes to Lead Radar, not the active pipeline.

Background: N0040626Q0450 (NAVSUP FLC Puget Sound, 2026-09-10 ingest) is titled
"Standard Beds, Box Springs, Mattresses & Headboards" and scored fit 85 on the
title alone, so it entered bids/active/_pipeline.csv as a confirmed bid. The
solicitation is 32 CLINs of aluminum/CRES shipboard berthing built to NAVSEA
drawings, NAICS 337127, delivered FPO Yokosuka, Japan. The relevance gate reads
text only; these tests pin the structured second look.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ingest_sam  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "sam_response.json"

NAVY = {
    "noticeId": "de52ec8f8f004040a4b1891fcebb5beb",
    "solicitationNumber": "N0040626Q0450",
    "title": 'Procurement of - "Standard Beds, Box Springs, Mattresses & Headboards" Aboard Naval Vessel',
    "fullParentPathName": "DEPT OF DEFENSE.DEPT OF THE NAVY.NAVSUP.NAVSUP FLC PUGET SOUND",
    "naicsCode": "337127",
    "classificationCode": "7195",
    "type": "Solicitation",
    "typeOfSetAside": "SBA",
    "typeOfSetAsideDescription": "Small Business Set Aside - Total",
    "postedDate": "2026-09-10",
    "responseDeadLine": "2026-09-14T12:00:00-07:00",
    "placeOfPerformance": {"country": {"code": "JPN", "name": "JAPAN"}},
}


class PlaceOfPerformanceTests(unittest.TestCase):
    def test_domestic_row_keeps_city_state_form(self) -> None:
        pop = {"city": {"name": "Houston"}, "state": {"code": "TX"}, "country": {"code": "USA", "name": "UNITED STATES"}}
        self.assertEqual(ingest_sam._extract_place_of_performance(pop), "Houston, TX")
        self.assertFalse(ingest_sam._is_foreign_place_of_performance(pop))

    def test_foreign_row_names_the_country(self) -> None:
        self.assertEqual(ingest_sam._extract_place_of_performance(NAVY["placeOfPerformance"]), "Japan")
        with_city = {"city": {"name": "Yokosuka"}, "country": {"code": "JPN", "name": "JAPAN"}}
        self.assertEqual(ingest_sam._extract_place_of_performance(with_city), "Yokosuka, Japan")
        self.assertTrue(ingest_sam._is_foreign_place_of_performance(with_city))

    def test_missing_country_is_not_treated_as_foreign(self) -> None:
        self.assertFalse(ingest_sam._is_foreign_place_of_performance(None))
        self.assertFalse(ingest_sam._is_foreign_place_of_performance({"city": {"name": "Gulfport"}, "state": {"code": "MS"}}))
        self.assertEqual(ingest_sam._extract_place_of_performance({"city": {"name": "Gulfport"}, "state": {"code": "MS"}}), "Gulfport, MS")


class DemotionReasonTests(unittest.TestCase):
    def test_navy_record_is_demoted_for_both_reasons(self) -> None:
        reason = ingest_sam.active_scope_demotion(NAVY)
        self.assertIn("place of performance outside the US (JAPAN)", reason)
        self.assertIn("NAICS 337127 is not a mattress code", reason)

    def test_mattress_naics_domestic_record_is_not_demoted(self) -> None:
        with FIXTURE.open("r", encoding="utf-8") as fh:
            rec = json.load(fh)["opportunitiesData"][0]
        self.assertEqual(rec["naicsCode"], "337910")
        self.assertEqual(ingest_sam.active_scope_demotion(rec), "")

    def test_furniture_retail_naics_is_allowed(self) -> None:
        rec = dict(NAVY, naicsCode="449110", placeOfPerformance={"city": {"name": "Gulfport"}, "state": {"code": "MS"},
                                                                  "country": {"code": "USA", "name": "UNITED STATES"}})
        self.assertEqual(ingest_sam.active_scope_demotion(rec), "")

    def test_blank_naics_is_not_a_reason(self) -> None:
        rec = dict(NAVY, naicsCode="", placeOfPerformance=None)
        self.assertEqual(ingest_sam.active_scope_demotion(rec), "")


class IngestRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        with FIXTURE.open("r", encoding="utf-8") as fh:
            self.fixture = json.load(fh)["opportunitiesData"]

    def test_navy_notice_routes_to_lead_radar_not_active(self) -> None:
        new_rows, leads, dupes, rejected = ingest_sam.ingest([NAVY], [], today="2026-09-10")
        self.assertEqual(new_rows, [], "shipboard berthing must not enter the active pipeline")
        self.assertEqual(rejected, [], "the row is kept for a human look, not dropped")
        self.assertEqual(len(leads), 1)
        lead = leads[0]
        self.assertEqual(lead["solicitation_number"], "N0040626Q0450")
        self.assertIn("active-scope gate: place of performance outside the US (JAPAN)", lead["notes"])
        self.assertIn("NAICS 337127 is not a mattress code", lead["notes"])

    def test_us_mattress_naics_still_enters_active_pipeline(self) -> None:
        new_rows, leads, _dupes, _rej = ingest_sam.ingest(self.fixture[:1], [], today="2026-05-14")
        self.assertEqual(len(new_rows), 1)
        self.assertEqual(leads, [])
        self.assertEqual(new_rows[0]["delivery_location"], "Houston, TX")

    def test_us_mattress_title_under_other_naics_goes_to_lead_radar(self) -> None:
        rec = dict(NAVY, solicitationNumber="X-337127-US", title="Twin XL dormitory mattresses",
                   placeOfPerformance={"city": {"name": "San Antonio"}, "state": {"code": "TX"},
                                       "country": {"code": "USA", "name": "UNITED STATES"}})
        new_rows, leads, _dupes, _rej = ingest_sam.ingest([rec], [], today="2026-09-10")
        self.assertEqual(new_rows, [])
        self.assertEqual(len(leads), 1)
        self.assertIn("NAICS 337127 is not a mattress code", leads[0]["notes"])
        self.assertNotIn("outside the US", leads[0]["notes"])

    def test_reject_grade_is_untouched_by_the_gate(self) -> None:
        rec = dict(NAVY, solicitationNumber="ROOF-1", title="Bunkhouse roof repairs", naicsCode="238160")
        new_rows, leads, _dupes, rejected = ingest_sam.ingest([rec], [], today="2026-09-10")
        self.assertEqual((new_rows, leads), ([], []))
        self.assertEqual(len(rejected), 1)
        self.assertNotIn("active-scope gate", rejected[0]["next_action"])


if __name__ == "__main__":
    unittest.main()
