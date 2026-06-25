"""Unit tests for tools/draft_bid_response.py. Stdlib unittest only."""

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

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import draft_bid_response as dbr  # noqa: E402
import pipeline  # noqa: E402


SCHEMA_PATH = ROOT / "vendor-profiles" / "vendor_profile.schema.json"


VALID_PROFILE = {
    "vendor": {"legal_name": "Acme Mattress Co"},
    "company": {
        "delivery_method": "own_fleet",
        "delivery_services": ["dock_delivery"],
        "service_geography": ["TX", "Houston"],
    },
    "products": {
        "dormitory_mattress": "yes",
        "correctional_mattress": "yes",
        "cot_mattress": "no",
        "bed_frames": "yes",
    },
    "compliance": {
        "spec_sheets": "available",
        "fire_safety": "available",
        "insurance": ["general_liability", "auto"],
        "certifications": [],
    },
    "reference_contracts": [
        {"buyer": "City of Houston", "solicitation": "IFB-001", "reference_available": True}
    ],
    "target_buyers": {"highest": ["cities"]},
    "contract_preferences": {
        "fixed_price_comfort": "maybe; needs escalation",
        "pricing_constraints": "foam cost volatility",
        "preferred_types": ["annual", "multi_year"],
    },
    "portal_status": [
        {"portal": "Texas CMBL", "status": "registered", "next_step": "audit codes"}
    ],
    "setup_gaps": [
        "Confirm warranty terms by product category",
        "Decide minimum attractive contract size",
    ],
}


def _write_pipeline(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in pipeline.CANONICAL_HEADER})


def _opportunity(**overrides) -> dict:
    base = {
        "opportunity_id": "test-cmd-001",
        "status": "watching",
        "source": "Texas ESBD",
        "buyer": "Texas Facilities Commission",
        "solicitation_number": "IFB 529-XYZ",
        "title": "Dormitory mattresses pilot",
        "primary_products": "Twin XL dormitory mattresses; bed frames",
        "commodity_terms": "mattresses; dormitory furniture",
        "delivery_location": "Austin TX",
        "estimated_value": "12500",
        "fit_score": "75",
        "risk_level": "low",
    }
    base.update(overrides)
    return base


class PureFunctionTests(unittest.TestCase):
    def test_product_fit_intersection(self) -> None:
        opp = _opportunity()
        fit = dbr.compute_product_fit(VALID_PROFILE, opp)
        # dormitory_mattress matches (humanized → "dormitory mattress" appears
        # in "twin xl dormitory mattresses; bed frames"). bed_frames matches
        # (humanized → "bed frames"). correctional_mattress does not.
        self.assertIn("dormitory_mattress", fit)
        self.assertIn("bed_frames", fit)
        self.assertNotIn("correctional_mattress", fit)
        # cot_mattress is "no" — must not match even if text mentions cots.
        self.assertNotIn("cot_mattress", fit)

    def test_compliance_gaps_render_as_tbd(self) -> None:
        status = dbr.compute_compliance_status(VALID_PROFILE)
        self.assertEqual(status["spec_sheets"], "available")
        self.assertEqual(status["insurance"], "available")
        # Not set in VALID_PROFILE → TBD
        self.assertEqual(status["warranty_terms"], "TBD")
        self.assertEqual(status["tamper_resistant"], "TBD")
        # Empty array → TBD
        self.assertEqual(status["certifications"], "TBD")

    def test_delivery_fit_in_and_out_of_geography(self) -> None:
        opp_in = _opportunity(delivery_location="Houston TX")
        result = dbr.compute_delivery_fit(VALID_PROFILE, opp_in)
        self.assertIn("inside listed service geography", result["coverage"])

        opp_out = _opportunity(delivery_location="Portland OR")
        result_out = dbr.compute_delivery_fit(VALID_PROFILE, opp_out)
        self.assertIn("outside the vendor's listed service geography", result_out["coverage"])

        opp_blank = _opportunity(delivery_location="")
        result_blank = dbr.compute_delivery_fit(VALID_PROFILE, opp_blank)
        self.assertIn("not stated", result_blank["coverage"])

    def test_delivery_fit_matches_state_abbreviation_against_full_name(self) -> None:
        # Profile uses full state names; SAM.gov locations use codes.
        profile = {"company": {"service_geography": ["Oklahoma", "Louisiana", "New Mexico"]}}
        for location in ("S Coffeyville, OK", "Saint Francisville, LA", "Albuquerque, NM"):
            result = dbr.compute_delivery_fit(profile, _opportunity(delivery_location=location))
            self.assertIn("inside listed service geography", result["coverage"], location)

    def test_delivery_fit_matches_full_name_against_abbreviation_profile(self) -> None:
        # Profile uses codes; opportunity spells the state out.
        profile = {"company": {"service_geography": ["TX"]}}
        result = dbr.compute_delivery_fit(profile, _opportunity(delivery_location="Austin, Texas"))
        self.assertIn("inside listed service geography", result["coverage"])

    def test_delivery_fit_abbreviation_not_matched_mid_word(self) -> None:
        # "LA" (Louisiana) must not match Los Angeles, and "Kansas" must
        # not match "Arkansas".
        la_profile = {"company": {"service_geography": ["Louisiana"]}}
        result = dbr.compute_delivery_fit(la_profile, _opportunity(delivery_location="Los Angeles, CA"))
        self.assertIn("outside the vendor's listed service geography", result["coverage"])

        ks_profile = {"company": {"service_geography": ["Kansas"]}}
        result_ks = dbr.compute_delivery_fit(ks_profile, _opportunity(delivery_location="Little Rock, Arkansas"))
        self.assertIn("outside the vendor's listed service geography", result_ks["coverage"])

    def test_decision_suggestion(self) -> None:
        self.assertEqual(dbr.decision_suggestion(_opportunity(risk_level="low")), "bid")
        self.assertEqual(dbr.decision_suggestion(_opportunity(risk_level="medium")), "evaluate")
        self.assertEqual(dbr.decision_suggestion(_opportunity(risk_level="high")), "no-bid candidate")
        self.assertEqual(
            dbr.decision_suggestion(_opportunity(risk_level="low", procurement_risk="blocker")),
            "blocked pending procurement gate",
        )
        self.assertEqual(
            dbr.decision_suggestion(_opportunity(risk_level="low", procurement_risk="high")),
            "evaluate procurement blocker",
        )
        self.assertIn("TBD", dbr.decision_suggestion(_opportunity(risk_level="")))

    def test_past_performance_detection(self) -> None:
        self.assertTrue(dbr.has_past_performance(VALID_PROFILE))
        no_refs = {**VALID_PROFILE, "reference_contracts": []}
        self.assertFalse(dbr.has_past_performance(no_refs))
        unavailable = {
            **VALID_PROFILE,
            "reference_contracts": [{"buyer": "X", "solicitation": "Y", "reference_available": False}],
        }
        self.assertFalse(dbr.has_past_performance(unavailable))


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.archive = self.tmp / "archive.csv"
        self.profile = self.tmp / "acme.profile.json"
        self.out = self.tmp / "drafts"

        self.profile.write_text(json.dumps(VALID_PROFILE), encoding="utf-8")
        _write_pipeline(self.active, [_opportunity()])
        _write_pipeline(self.archive, [_opportunity(opportunity_id="old-001", status="awarded")])

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = dbr.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def _common(self, opp_id: str = "test-cmd-001") -> list[str]:
        return [
            opp_id,
            "--vendor", str(self.profile),
            "--active", str(self.active),
            "--archive", str(self.archive),
            "--schema", str(SCHEMA_PATH),
            "--output-dir", str(self.out),
            "--generated-date", "2026-05-14",
        ]

    def test_happy_path_writes_markdown(self) -> None:
        rc, out, err = self._run(*self._common())
        self.assertEqual(rc, 0, err)
        draft = self.out / "test-cmd-001_draft.md"
        self.assertTrue(draft.exists())
        body = draft.read_text(encoding="utf-8")
        self.assertIn("# Dormitory mattresses pilot", body)
        self.assertIn("Acme Mattress Co", body)
        self.assertIn("dormitory mattress", body)
        self.assertIn("| Procurement risk |", body)
        self.assertIn("| Gate status |", body)
        self.assertIn("| Compliance blocker |", body)
        # Provenance line is rendered
        self.assertIn("Draft generated 2026-05-14", body)
        # Decision suggestion lands in section 7
        self.assertIn("Suggested:** bid", body)

    def test_unknown_opportunity_id_errors(self) -> None:
        rc, _, err = self._run(*self._common("does-not-exist"))
        self.assertEqual(rc, 1)
        self.assertIn("not found", err)

    def test_falls_back_to_archive(self) -> None:
        rc, _, err = self._run(*self._common("old-001"))
        self.assertEqual(rc, 0, err)
        draft = self.out / "old-001_draft.md"
        self.assertTrue(draft.exists())
        body = draft.read_text(encoding="utf-8")
        self.assertIn("(archive)", body)

    def test_schema_validation_failure_aborts(self) -> None:
        bad_profile = self.tmp / "bad.profile.json"
        bad_profile.write_text(json.dumps({"vendor": {"legal_name": ""}}), encoding="utf-8")
        argv = self._common()
        argv[argv.index("--vendor") + 1] = str(bad_profile)
        rc, _, err = self._run(*argv)
        self.assertEqual(rc, 1)
        self.assertIn("schema validation", err)
        # No draft should have been written.
        self.assertFalse((self.out / "test-cmd-001_draft.md").exists())

    def test_refuses_overwrite_without_force(self) -> None:
        rc, _, _ = self._run(*self._common())
        self.assertEqual(rc, 0)
        rc2, _, err = self._run(*self._common())
        self.assertEqual(rc2, 1)
        self.assertIn("already exists", err)

    def test_force_overwrites(self) -> None:
        rc, _, _ = self._run(*self._common())
        self.assertEqual(rc, 0)
        draft = self.out / "test-cmd-001_draft.md"
        first_mtime = draft.stat().st_mtime_ns
        argv = self._common() + ["--force"]
        rc2, _, err = self._run(*argv)
        self.assertEqual(rc2, 0, err)
        self.assertGreaterEqual(draft.stat().st_mtime_ns, first_mtime)

    def test_output_is_deterministic_given_generated_date(self) -> None:
        rc, _, _ = self._run(*self._common())
        self.assertEqual(rc, 0)
        first = (self.out / "test-cmd-001_draft.md").read_text(encoding="utf-8")
        (self.out / "test-cmd-001_draft.md").unlink()
        rc2, _, _ = self._run(*self._common())
        self.assertEqual(rc2, 0)
        second = (self.out / "test-cmd-001_draft.md").read_text(encoding="utf-8")
        self.assertEqual(first, second)

    def test_bad_generated_date_rejected(self) -> None:
        argv = list(self._common())
        argv[argv.index("--generated-date") + 1] = "yesterday"
        rc, _, err = self._run(*argv)
        self.assertEqual(rc, 2)  # argparse error exit
        self.assertIn("YYYY-MM-DD", err)


class ComplianceChecklistTests(unittest.TestCase):
    """Make sure the Required Documents checklist reflects profile state."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.archive = self.tmp / "archive.csv"
        _write_pipeline(self.active, [_opportunity()])
        _write_pipeline(self.archive, [])

    def _draft_with_profile(self, profile: dict, generated_date: str = "2026-05-14") -> str:
        profile_path = self.tmp / "acme.profile.json"
        profile_path.write_text(json.dumps(profile), encoding="utf-8")
        out = self.tmp / "drafts"
        rc = dbr.main([
            "test-cmd-001",
            "--vendor", str(profile_path),
            "--active", str(self.active),
            "--archive", str(self.archive),
            "--schema", str(SCHEMA_PATH),
            "--output-dir", str(out),
            "--generated-date", generated_date,
        ])
        self.assertEqual(rc, 0)
        return (out / "test-cmd-001_draft.md").read_text(encoding="utf-8")

    def test_checked_items_when_profile_complete(self) -> None:
        body = self._draft_with_profile(VALID_PROFILE)
        # Insurance present → checked
        self.assertIn("[x] Insurance certificates", body)
        # Spec sheets present → checked
        self.assertIn("[x] Product specification sheets", body)
        # Past-performance reference available → checked
        self.assertIn("[x] Past-performance references", body)

    def test_unchecked_items_when_profile_thin(self) -> None:
        thin = {
            "vendor": {"legal_name": "Thin Co"},
            "company": {"delivery_method": "unknown"},
            "products": {},
            "compliance": {},
            "target_buyers": {},
            "portal_status": [],
        }
        body = self._draft_with_profile(thin)
        self.assertIn("[ ] Insurance certificates", body)
        self.assertIn("[ ] Product specification sheets", body)
        self.assertIn("[ ] Past-performance references", body)
        # TBD markers should appear next to unchecked items.
        self.assertIn("TBD", body)


if __name__ == "__main__":
    unittest.main()
