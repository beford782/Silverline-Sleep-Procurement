"""Set-aside eligibility gate: readiness.py detection + ingest_sam.py stamping.

Background: SAM 140A2326Q0283 (BIE / Haskell, 2026-08-27 ingest) scored fit 95
and landed in the active pipeline although the notice was "SET-ASIDE 100% FOR
INDIAN SMALL BUSINESS ECONOMIC ENTERPRISES" - the relevance gate never reads
eligibility. These tests pin the fix: the code is stamped into notes, readiness
turns it into a blocker unless it is in configs/capabilities.json
set_aside_eligibility, and ingest blocks the row on arrival.
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
import pipeline  # noqa: E402
import readiness  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "sam_response.json"
CAPS = dict(readiness.DEFAULT_CAPS, sam_active=True)


def row(**kw) -> dict:
    base = {k: "" for k in pipeline.CANONICAL_HEADER}
    base.update(kw)
    return base


class SetAsideReadinessTests(unittest.TestCase):
    def test_isbee_stamp_is_a_blocker(self) -> None:
        r = row(title="Residential Housing Mattresses", source="SAM.gov", buyer="Interior BIA",
                notes="Solicitation | Set-aside: ISBEE (Indian Small Business Economic Enterprise)")
        self.assertIn("set-aside eligibility: ISBEE", readiness.requirements_for(r))
        self.assertIn("set-aside: ISBEE (not eligible)", readiness.blockers_for(r, CAPS))

    def test_total_small_business_is_met(self) -> None:
        r = row(title="CRTC Replacement Mattresses", source="SAM.gov", buyer="USPFO MS",
                notes="Combined Synopsis/Solicitation | Set-aside: SBA (Total Small Business Set-Aside)")
        self.assertIn("set-aside eligibility: SBA", readiness.requirements_for(r))
        self.assertEqual(readiness.blockers_for(r, CAPS), [])

    def test_prose_set_aside_mentions_do_not_match(self) -> None:
        r = row(title="Mattresses", source="SAM.gov", buyer="Air Force",
                notes="Total small-business set-aside, NAICS 449110 size std $25M; "
                      "'projected to be a small business set-aside'; no set-aside declared yet")
        self.assertNotIn("set_aside", [q.cap_key for q in readiness._detect(r)])

    def test_none_code_is_open_competition(self) -> None:
        r = row(title="Mattresses", source="SAM.gov", buyer="Navy", notes="Solicitation | Set-aside: NONE")
        self.assertEqual([q for q in readiness.requirements_for(r) if "set-aside" in q], [])
        self.assertFalse(readiness.set_aside_ineligible("NONE", CAPS))
        self.assertFalse(readiness.set_aside_ineligible("", CAPS))

    def test_helper_follows_capabilities(self) -> None:
        self.assertTrue(readiness.set_aside_ineligible("ISBEE", CAPS))
        self.assertTrue(readiness.set_aside_ineligible("8A", CAPS))
        self.assertFalse(readiness.set_aside_ineligible("sba", CAPS))
        wider = dict(CAPS, set_aside_eligibility=["SBA", "SBP", "HZC"])
        self.assertFalse(readiness.set_aside_ineligible("HZC", wider))

    def test_repo_capabilities_file_declares_small_business_codes(self) -> None:
        data = json.loads((ROOT / "configs" / "capabilities.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(data["set_aside_eligibility"]), ["SBA", "SBP"])

    def test_annotate_blocks_stamped_row_and_clears_eligible_one(self) -> None:
        blocked = row(opportunity_id="bia", title="Residential Housing Mattresses", source="SAM.gov",
                      buyer="Interior BIA", notes="Set-aside: ISBEE", gate_status="bid_ready")
        fine = row(opportunity_id="crtc", title="CRTC Replacement Mattresses", source="SAM.gov",
                   buyer="USPFO MS", notes="Set-aside: SBA", gate_status="blocked", procurement_risk="blocker")
        readiness.annotate([blocked, fine], CAPS, "2026-08-31")
        self.assertEqual(blocked["gate_status"], "blocked")
        self.assertEqual(blocked["compliance_blocker"], "set-aside: ISBEE (not eligible)")
        self.assertEqual(fine["gate_status"], "bid_ready")
        self.assertEqual(fine["compliance_blocker"], "")


class SetAsideIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        with FIXTURE.open("r", encoding="utf-8") as fh:
            self.record = json.load(fh)["opportunitiesData"][0]

    def test_ineligible_set_aside_is_blocked_on_arrival(self) -> None:
        rec = dict(self.record, typeOfSetAside="ISBEE",
                   typeOfSetAsideDescription="Indian Small Business Economic Enterprise (ISBEE)")
        r = ingest_sam.record_to_row(rec, today="2026-08-27")
        self.assertIn("Set-aside: ISBEE (Indian Small Business Economic Enterprise (ISBEE))", r["notes"])
        self.assertTrue(r["compliance_blocker"].startswith("set_aside_ineligible:ISBEE; "))
        self.assertTrue(r["compliance_blocker"].endswith("specs_pending"))
        self.assertEqual(r["gate_status"], "blocked")
        self.assertTrue(r["next_action"].startswith("NO-BID CANDIDATE: ISBEE set-aside"))
        # readiness re-derives the same conclusion from the stamp alone.
        self.assertIn("set-aside: ISBEE (not eligible)", readiness.blockers_for(r, CAPS))

    def test_small_business_set_aside_is_stamped_but_not_blocked(self) -> None:
        rec = dict(self.record, typeOfSetAside="SBA", typeOfSetAsideDescription="Total Small Business Set-Aside (FAR 19.5)")
        r = ingest_sam.record_to_row(rec, today="2026-08-27")
        self.assertIn("Set-aside: SBA (Total Small Business Set-Aside (FAR 19.5))", r["notes"])
        self.assertNotIn("set_aside_ineligible", r["compliance_blocker"])
        self.assertTrue(r["next_action"].startswith("Triage:"))

    def test_no_set_aside_leaves_row_unchanged(self) -> None:
        r = ingest_sam.record_to_row(self.record, today="2026-08-27")
        self.assertEqual(r["notes"], (self.record.get("type") or "").strip())
        self.assertNotIn("set_aside_ineligible", r["compliance_blocker"])
        self.assertTrue(r["next_action"].startswith("Triage:"))


if __name__ == "__main__":
    unittest.main()
