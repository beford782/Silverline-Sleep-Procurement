"""Unit tests for tools/demand_signal.py. Stdlib unittest, no I/O.

These mirror tests/test_relevance.py: tools/ is put on sys.path, the module is
imported directly, and assertions check the banded decision plus the structured
fields (segment, scale, stage, dates, buy window). A tripwire test confirms this
PR did not disturb relevance.classify().
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import demand_signal  # noqa: E402
import relevance  # noqa: E402


class AcceptTests(unittest.TestCase):
    def test_hotel_groundbreaking_accepts(self) -> None:
        v = demand_signal.classify_demand(
            "Marriott breaks ground on 180-key Fairfield Inn in Frisco, TX, "
            "opening Q3 2027"
        )
        self.assertEqual(v.decision, "ACCEPT")
        self.assertEqual(v.segment, "hotel")
        self.assertEqual(v.scale_value, 180)
        self.assertIn(v.scale_unit, ("keys", "key"))
        self.assertEqual(v.project_stage, "under-construction")
        self.assertEqual(v.est_buy_window, "2027-09")
        self.assertIn("TX", v.states)

    def test_senior_living_renovation_accepts(self) -> None:
        v = demand_signal.classify_demand(
            "Brookdale assisted living community in Tyler, TX begins a "
            "property improvement plan renovation of all resident rooms"
        )
        self.assertEqual(v.decision, "ACCEPT")
        self.assertEqual(v.segment, "senior-living")
        self.assertEqual(v.project_stage, "renovation")

    def test_student_housing_accepts(self) -> None:
        v = demand_signal.classify_demand(
            "University breaks ground on new residence hall with 600 beds in "
            "Austin, TX, opening Fall 2026"
        )
        self.assertEqual(v.decision, "ACCEPT")
        self.assertEqual(v.segment, "student-housing")
        self.assertEqual(v.scale_value, 600)


class RejectTests(unittest.TestCase):
    def test_office_construction_rejects(self) -> None:
        v = demand_signal.classify_demand(
            "Developer breaks ground on 12-story office tower downtown"
        )
        self.assertEqual(v.decision, "REJECT")

    def test_no_facility_rejects(self) -> None:
        v = demand_signal.classify_demand(
            "City approves new highway interchange and parking garage"
        )
        self.assertEqual(v.decision, "REJECT")

    def test_mattress_retail_noise_rejects(self) -> None:
        # Mattress *retail* noise with no facility is not a demand signal.
        v = demand_signal.classify_demand("Mattress Firm announces a holiday sale")
        self.assertEqual(v.decision, "REJECT")


class ReviewTests(unittest.TestCase):
    def test_facility_without_project_verb_is_review(self) -> None:
        v = demand_signal.classify_demand(
            "Guests enjoyed their stay at the downtown Hyatt Regency"
        )
        self.assertEqual(v.decision, "REVIEW")
        self.assertEqual(v.segment, "hotel")

    def test_out_of_region_demotes_to_review(self) -> None:
        v = demand_signal.classify_demand(
            "Hilton breaks ground on a 200-room resort in San Diego, "
            "California, opening 2028",
            home_states=relevance.HOME_STATES_DEFAULT,
        )
        self.assertEqual(v.decision, "REVIEW")
        self.assertIn("CA", v.states)
        self.assertIn("out-of-region", "; ".join(v.reasons))

    def test_out_of_region_in_custom_home_states_stays_accept(self) -> None:
        # Same headline, but California is the home area -> stays ACCEPT.
        v = demand_signal.classify_demand(
            "Hilton breaks ground on a 200-room resort in San Diego, "
            "California, opening 2028",
            home_states=frozenset({"CA"}),
        )
        self.assertEqual(v.decision, "ACCEPT")


class ScaleTests(unittest.TestCase):
    def test_scale_extraction_takes_max_and_strips_commas(self) -> None:
        v = demand_signal.classify_demand(
            "New 1,200-bed correctional facility under construction; an initial "
            "wing of 80 beds opens first"
        )
        self.assertEqual(v.scale_value, 1200)
        self.assertEqual(v.segment, "correctional")


class DateTests(unittest.TestCase):
    def test_date_and_buy_window(self) -> None:
        v = demand_signal.classify_demand("New Hilton hotel opening Q4 2027")
        self.assertEqual(v.est_completion_date, "2027")
        self.assertEqual(v.est_buy_window, "2027-12")

    def test_no_date_yields_empty_buy_window(self) -> None:
        v = demand_signal.classify_demand("New Hilton hotel breaks ground downtown")
        self.assertEqual(v.est_completion_date, "")
        self.assertEqual(v.est_buy_window, "")


class RelevanceUntouchedTests(unittest.TestCase):
    """Tripwire: this PR must not change relevance.classify()'s behavior."""

    def test_relevance_classify_untouched(self) -> None:
        v = relevance.classify(
            "Invitation to Bid: 80 Twin XL mattresses and box springs"
        )
        self.assertEqual(v.decision, "ACCEPT")
        self.assertIn("mattresses", v.matched_include)


if __name__ == "__main__":
    unittest.main()
