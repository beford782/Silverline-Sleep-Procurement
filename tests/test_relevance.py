"""Unit tests for tools/relevance.py. Stdlib unittest, no I/O."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import relevance  # noqa: E402


class AcceptTests(unittest.TestCase):
    def test_explicit_mattress_accepts(self) -> None:
        v = relevance.classify("Dormitory Mattresses and Bed Frames")
        self.assertEqual(v.decision, "ACCEPT")
        self.assertIn("mattresses", v.matched_include)
        self.assertGreaterEqual(v.confidence, 80)

    def test_box_spring_accepts(self) -> None:
        self.assertEqual(relevance.classify("Box Springs and foundations").decision, "ACCEPT")

    def test_dormitory_mattress_accepts(self) -> None:
        v = relevance.classify("Dormitory mattress replacement program")
        self.assertEqual(v.decision, "ACCEPT")
        self.assertIn("dormitory mattress", v.matched_include)

    def test_in_region_stays_accept(self) -> None:
        v = relevance.classify("Fire-retardant jail mattresses, S Coffeyville, OK")
        self.assertEqual(v.decision, "ACCEPT")
        self.assertIn("OK", v.states)


class ReviewTests(unittest.TestCase):
    def test_furniture_only_is_review(self) -> None:
        v = relevance.classify("Office - Supplies, Equipment, Furniture & Services")
        self.assertEqual(v.decision, "REVIEW")
        self.assertIn("furniture", v.matched_include)

    def test_school_furniture_is_review(self) -> None:
        self.assertEqual(relevance.classify("School Furniture & Related Services").decision, "REVIEW")

    def test_twin_xl_dorm_is_review(self) -> None:
        # "Twin XL" is a student-housing size signal but not an explicit
        # mattress term, so it surfaces for human triage rather than rejecting.
        v = relevance.classify("University residence hall Twin XL replacement RFP")
        self.assertEqual(v.decision, "REVIEW")
        self.assertIn("twin xl", v.matched_include)

    def test_out_of_region_mattress_demoted_to_review(self) -> None:
        v = relevance.classify("Hospital mattresses and box springs, Sacramento, CA")
        self.assertEqual(v.decision, "REVIEW")
        self.assertIn("out-of-region: CA", "; ".join(v.reasons))

    def test_full_state_name_out_of_region(self) -> None:
        v = relevance.classify("Mattresses for the State of California correctional system")
        self.assertEqual(v.decision, "REVIEW")
        self.assertIn("CA", v.states)


class RejectTests(unittest.TestCase):
    def test_registration_email_rejected(self) -> None:
        v = relevance.classify("TIPS eBid System Registration Activation Notification")
        self.assertEqual(v.decision, "REJECT")

    def test_concrete_mattress_rejected(self) -> None:
        v = relevance.classify("Articulated concrete mattress for erosion control")
        self.assertEqual(v.decision, "REJECT")
        self.assertTrue(v.matched_exclude or "hard-exclude" in "; ".join(v.reasons))

    def test_air_mattress_rejected(self) -> None:
        self.assertEqual(relevance.classify("Inflatable air mattress consumer goods").decision, "REJECT")

    def test_recycling_rejected(self) -> None:
        self.assertEqual(relevance.classify("Mattress recycling services contract").decision, "REJECT")


class WordBoundaryTests(unittest.TestCase):
    def test_cot_does_not_match_scott(self) -> None:
        # "cot" must not fire inside "Scott"; no other signal -> REJECT.
        v = relevance.classify("Scott County paving and asphalt services")
        self.assertEqual(v.decision, "REJECT")

    def test_foundation_word_boundary(self) -> None:
        # "foundation" as a standalone weak term matches; "foundational" should not
        # alone create a mattress signal beyond the weak tier.
        v = relevance.classify("Foundational leadership training seminar")
        self.assertEqual(v.decision, "REJECT")


class ProcurementCueTests(unittest.TestCase):
    def test_mattress_news_without_cue_demoted(self) -> None:
        # A news headline with a mattress term but no procurement cue.
        v = relevance.classify("Woman arrested for ripping up jail mattress",
                               require_procurement=True)
        self.assertEqual(v.decision, "REVIEW")

    def test_mattress_with_bid_cue_accepts(self) -> None:
        v = relevance.classify("Invitation for bid: correctional mattresses",
                               require_procurement=True)
        self.assertEqual(v.decision, "ACCEPT")

    def test_require_procurement_off_keeps_accept(self) -> None:
        # Without the flag (e.g. SAM/email channels), no cue is needed.
        v = relevance.classify("jail mattress", require_procurement=False)
        self.assertEqual(v.decision, "ACCEPT")

    def test_has_procurement_cue(self) -> None:
        self.assertTrue(relevance.has_procurement_cue("Request for Proposal #12"))
        self.assertFalse(relevance.has_procurement_cue("a comfy night of sleep"))


class GeographyTests(unittest.TestCase):
    def test_detect_states_name_and_code(self) -> None:
        s = relevance.detect_states("Delivery to Dallas, TX and also Louisiana")
        self.assertEqual(s, {"TX", "LA"})

    def test_custom_home_states(self) -> None:
        v = relevance.classify("Mattresses, Phoenix, AZ", home_states=frozenset({"AZ"}))
        self.assertEqual(v.decision, "ACCEPT")


if __name__ == "__main__":
    unittest.main()
