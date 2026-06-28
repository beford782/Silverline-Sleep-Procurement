"""Unit tests for tools/win_score.py. Stdlib unittest."""

from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import relevance  # noqa: E402
import win_score  # noqa: E402

TODAY = date(2026, 6, 28)


def row(**kw) -> dict:
    """A pipeline-ish row with sensible blanks."""
    base = {
        "opportunity_id": "r", "title": "", "primary_products": "",
        "commodity_terms": "", "trigger_terms": "", "buyer": "", "source": "",
        "delivery_location": "", "estimated_value": "", "due_date": "",
        "notes": "", "lead_type": "",
    }
    base.update(kw)
    return base


class ValueTierTests(unittest.TestCase):
    def test_buckets(self) -> None:
        self.assertEqual(win_score.value_tier(row(estimated_value="10000")), 0.5)
        self.assertEqual(win_score.value_tier(row(estimated_value="50000")), 0.8)
        self.assertEqual(win_score.value_tier(row(estimated_value="200000")), 1.0)
        self.assertEqual(win_score.value_tier(row(estimated_value="800000")), 1.2)

    def test_blank_value_is_neutral(self) -> None:
        self.assertEqual(win_score.value_tier(row(estimated_value="")), 0.7)

    def test_blank_value_with_currency_symbols(self) -> None:
        self.assertEqual(win_score.value_tier(row(estimated_value="$58,000")), 0.8)

    def test_bedcount_backfill(self) -> None:
        # "80 Twin XL" -> 80 x $120 = $9,600 -> <25k -> 0.5
        r = row(estimated_value="", title="Residence hall 80 Twin XL mattresses")
        self.assertEqual(win_score.value_tier(r), 0.5)

    def test_bedcount_backfill_large(self) -> None:
        # 1000 beds x $120 = $120k -> 100-500k bucket -> 1.0
        r = row(estimated_value="", title="State prison 1000 beds")
        self.assertEqual(win_score.value_tier(r), 1.0)


class WinProbabilityTests(unittest.TestCase):
    def test_in_region_vs_out_of_region(self) -> None:
        in_r = win_score.win_probability(
            row(title="Mattresses", buyer="Harris County, TX"), TODAY)
        out_r = win_score.win_probability(
            row(title="Mattresses", buyer="Cook County, IL"), TODAY)
        self.assertGreater(in_r, out_r)
        # in-region (1.0) x incumbent default (0.8) = 0.8
        self.assertAlmostEqual(in_r, 0.8, places=2)
        # out-of-region (0.3) x 0.8 = 0.24
        self.assertAlmostEqual(out_r, 0.24, places=2)

    def test_no_state_detected_mild_discount(self) -> None:
        wp = win_score.win_probability(row(title="Mattresses"), TODAY)
        # none detected (0.85) x incumbent default (0.8) = 0.68
        self.assertAlmostEqual(wp, 0.68, places=2)

    def test_brand_restrict_sinks_hard(self) -> None:
        # Norix brand restriction in an in-region buy: brand factor dominates.
        wp = win_score.win_probability(
            row(title="Norix BN furniture", buyer="State of Texas"), TODAY)
        self.assertLess(wp, 0.06)
        self.assertGreater(wp, 0.0)

    def test_sam_federal_blocked_is_zero(self) -> None:
        # capabilities.json ships sam_active=false, so a federal/SAM buy -> 0.
        self.assertFalse(win_score.sam_active())
        wp = win_score.win_probability(
            row(title="Bed mattress", source="SAM.gov", buyer="Dept of Defense Army"),
            TODAY)
        self.assertEqual(wp, 0.0)

    def test_past_due_sinks(self) -> None:
        wp = win_score.win_probability(
            row(title="Mattresses", buyer="Harris County, TX", due_date="2026-05-01"),
            TODAY)
        # in-region (1.0) x past-due (0.1) x incumbent (0.8) = 0.08
        self.assertAlmostEqual(wp, 0.08, places=2)

    def test_awarded_watch_exempt_from_past_due(self) -> None:
        # An awarded_contract_watch row is intentionally dated in the past; the
        # past-due gate must NOT apply to it.
        wp = win_score.win_probability(
            row(title="Mattresses", buyer="State of Texas", due_date="2026-05-01",
                lead_type="awarded_contract_watch"),
            TODAY)
        self.assertGreater(wp, 0.5)

    def test_reject_relevance_sinks(self) -> None:
        # A hard-exclude (concrete mattress) is REJECT -> x0.3 plus matched_exclude.
        wp = win_score.win_probability(
            row(title="Articulated concrete mattress", buyer="Harris County, TX"),
            TODAY)
        self.assertLess(wp, 0.3)

    def test_incumbent_recent_award_more_vulnerable_discount(self) -> None:
        recent = win_score.win_probability(
            row(title="Mattresses", buyer="Harris County, TX", award_date="2026-06-01"),
            TODAY)
        none = win_score.win_probability(
            row(title="Mattresses", buyer="Harris County, TX"), TODAY)
        self.assertLess(recent, none)
        self.assertAlmostEqual(recent, 0.4, places=2)  # 1.0 x 0.4


class StrategicFitTests(unittest.TestCase):
    def test_home_tx_bonus(self) -> None:
        s = win_score.strategic_fit(row(title="Mattresses", buyer="Austin, TX"))
        self.assertGreater(s, 1.0)

    def test_core_segment_bonus(self) -> None:
        core = win_score.strategic_fit(
            row(title="Jail mattresses", lead_type="correctional_detention"))
        plain = win_score.strategic_fit(row(title="Mattresses"))
        self.assertGreater(core, plain)

    def test_recurring_bonus(self) -> None:
        rec = win_score.strategic_fit(
            row(title="Mattresses", lead_type="awarded_contract_watch"))
        self.assertGreaterEqual(rec, 1.2)


class ProductFitTests(unittest.TestCase):
    def test_strong_mattress_high(self) -> None:
        self.assertGreaterEqual(win_score.product_fit(row(title="Mattresses")), 0.8)

    def test_reject_zero(self) -> None:
        self.assertEqual(win_score.product_fit(row(title="Office paving services")), 0.0)


class ComputeTests(unittest.TestCase):
    def test_norix_brand_row_scores_low(self) -> None:
        score, _ = win_score.compute(
            row(title="Norix BN Furniture - Statewide", buyer="State of Louisiana",
                trigger_terms="furniture; Norix", lead_type="broad_furniture_ffe",
                due_date="2026-06-24"),
            TODAY)
        self.assertLess(score, 10)

    def test_in_region_correctional_mattress_scores_high(self) -> None:
        score, factors = win_score.compute(
            row(title="Correctional mattresses for county jail",
                buyer="Harris County, TX", primary_products="mattresses",
                estimated_value="200000", lead_type="correctional_detention",
                due_date="2026-12-31"),
            TODAY)
        self.assertGreater(score, 55)
        self.assertEqual(set(factors), {"pf", "vt", "wp", "sf"})

    def test_ordering_sane(self) -> None:
        live = row(title="Correctional mattresses for county jail",
                   buyer="Harris County, TX", primary_products="mattresses",
                   estimated_value="200000", lead_type="correctional_detention",
                   due_date="2026-12-31")
        norix = row(title="Norix BN Furniture", buyer="State of Louisiana",
                    trigger_terms="furniture; Norix", lead_type="broad_furniture_ffe",
                    due_date="2026-06-24")
        closed_incumbent = row(title="Mattresses statewide", buyer="State of Texas",
                               estimated_value="150000", award_date="2026-06-01")
        rows = [norix, live, closed_incumbent]
        ranked = sorted(rows, key=lambda r: -win_score.compute(r, TODAY)[0])
        self.assertEqual(ranked[0], live)
        # Norix (brand-restricted) and the closed-incumbent both sink below live.
        live_s = win_score.compute(live, TODAY)[0]
        self.assertGreater(live_s, win_score.compute(closed_incumbent, TODAY)[0])
        self.assertGreater(live_s, win_score.compute(norix, TODAY)[0])

    def test_factors_rounded_two_dp(self) -> None:
        _, factors = win_score.compute(row(title="Mattresses", buyer="Austin, TX"), TODAY)
        for v in factors.values():
            self.assertEqual(round(v, 2), v)


class FormatFactorsTests(unittest.TestCase):
    def test_compact_form(self) -> None:
        s = win_score.format_factors({"pf": 0.8, "vt": 1.0, "wp": 0.8, "sf": 1.15})
        self.assertEqual(s, "pf=0.80;vt=1.00;wp=0.80;sf=1.15")


class RelevanceTripwireTests(unittest.TestCase):
    def test_classify_untouched(self) -> None:
        # win_score must not have perturbed relevance.classify behavior.
        v = relevance.classify("Twin dormitory mattresses, box spring foundation")
        self.assertEqual(v.decision, "ACCEPT")
        self.assertGreaterEqual(v.confidence, 75)


if __name__ == "__main__":
    unittest.main()
