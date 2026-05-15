"""Unit tests for tools/pipeline.py. Stdlib unittest, tempfile-backed."""

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

import pipeline  # noqa: E402


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def _write_header_only(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(pipeline.CANONICAL_HEADER) + "\n")


class SourceRegistryTests(unittest.TestCase):
    def test_registry_parses(self) -> None:
        with (ROOT / "sources" / "procurement_sources.json").open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 12)

    def test_registry_entries_have_required_keys(self) -> None:
        required = {
            "name", "source_type", "official_url", "has_api", "requires_login",
            "intake_method", "geography", "buyer_level", "search_terms",
            "commodity_terms", "cadence", "notes",
        }
        valid_intake = {"api", "saved_search", "email_notification", "manual_review", "csv_export", "portal_registration"}
        valid_cadence = {"daily", "weekly", "monthly", "ad_hoc"}
        valid_buyer_level = {"federal", "state", "county", "city", "isd", "university", "cooperative"}
        valid_source_type = {
            "federal_portal", "state_portal", "city_portal", "county_portal",
            "isd_portal", "university_portal", "vendor_database", "cooperative",
        }
        with (ROOT / "sources" / "procurement_sources.json").open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data:
            self.assertTrue(required <= set(entry.keys()), entry.get("name"))
            self.assertIn(entry["intake_method"], valid_intake, entry.get("name"))
            self.assertIn(entry["cadence"], valid_cadence, entry.get("name"))
            self.assertIn(entry["buyer_level"], valid_buyer_level, entry.get("name"))
            self.assertIn(entry["source_type"], valid_source_type, entry.get("name"))
            self.assertIsInstance(entry["search_terms"], list)
            self.assertIsInstance(entry["commodity_terms"], list)
            self.assertIsInstance(entry["has_api"], bool)
            self.assertIsInstance(entry["requires_login"], bool)


class HeaderParityTests(unittest.TestCase):
    def test_template_header_matches_active_pipeline_header(self) -> None:
        template_header, _ = _read_csv(ROOT / "templates" / "opportunity_tracker.csv")
        active_header, _ = _read_csv(ROOT / "bids" / "active" / "_pipeline.csv")
        archive_header, _ = _read_csv(ROOT / "bids" / "archive" / "_pipeline_archive.csv")
        self.assertEqual(template_header, pipeline.CANONICAL_HEADER)
        self.assertEqual(active_header, pipeline.CANONICAL_HEADER)
        self.assertEqual(archive_header, pipeline.CANONICAL_HEADER)


class PipelineCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp())
        self.active = self.tmpdir / "active.csv"
        self.archive = self.tmpdir / "archive.csv"
        _write_header_only(self.active)
        _write_header_only(self.archive)
        self.addCleanup(shutil.rmtree, str(self.tmpdir), True)

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = pipeline.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def _base_add_args(self, **overrides: str) -> list[str]:
        args = [
            "--active", str(self.active),
            "--archive", str(self.archive),
            "add",
            "--source", "Texas ESBD",
            "--buyer", "Texas Facilities Commission",
            "--solicitation-number", "IFB 529-XYZ",
            "--title", "Dormitory mattresses pilot",
        ]
        for k, v in overrides.items():
            args.append(f"--{k.replace('_', '-')}")
            args.append(v)
        return args

    def test_add_creates_a_row(self) -> None:
        rc, _, err = self._run(*self._base_add_args())
        self.assertEqual(rc, 0, err)
        _, rows = _read_csv(self.active)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["buyer"], "Texas Facilities Commission")
        self.assertEqual(rows[0]["status"], "watching")
        # last_reviewed and created_date default to today; just confirm they're present.
        self.assertTrue(rows[0]["created_date"])
        self.assertTrue(rows[0]["last_reviewed"])

    def test_add_rejects_duplicate_opportunity_id(self) -> None:
        rc, _, _ = self._run(*self._base_add_args())
        self.assertEqual(rc, 0)
        rc2, _, err = self._run(*self._base_add_args())
        self.assertEqual(rc2, 1)
        self.assertIn("already exists", err)

    def test_overwrite_flag_replaces_existing_row(self) -> None:
        rc, _, err = self._run(*self._base_add_args())
        self.assertEqual(rc, 0, err)
        argv = self._base_add_args(notes="updated")
        argv.append("--overwrite")
        rc2, _, err = self._run(*argv)
        self.assertEqual(rc2, 0, err)
        _, rows = _read_csv(self.active)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["notes"], "updated")

    def test_opportunity_id_is_stable(self) -> None:
        a = pipeline.derive_opportunity_id("Texas ESBD", "Texas Facilities Commission", "IFB 529-XYZ", "")
        b = pipeline.derive_opportunity_id("Texas ESBD", "Texas Facilities Commission", "IFB 529-XYZ", "anything")
        self.assertEqual(a, b)
        self.assertEqual(a, "texas-esbd-texas-facilities-commission-ifb-529-xyz")

    def test_opportunity_id_falls_back_to_title(self) -> None:
        oid = pipeline.derive_opportunity_id("Texas ESBD", "Texas Facilities Commission", "", "Dorm mattresses pilot")
        self.assertEqual(oid, "texas-esbd-texas-facilities-commission-dorm-mattresses-pilot")

    def test_invalid_date_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(due_date="2026/06/15"))
        self.assertEqual(rc, 1)
        self.assertIn("due_date", err)
        # No row should have been written.
        _, rows = _read_csv(self.active)
        self.assertEqual(rows, [])

    def test_invalid_status_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(status="maybe"))
        self.assertEqual(rc, 1)
        self.assertIn("status", err)

    def test_list_sorts_by_due_date_blanks_last(self) -> None:
        # Three rows: due 2026-07-01, due 2026-06-15, no due.
        argv = self._base_add_args(due_date="2026-07-01")
        self._run(*argv)
        argv2 = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "Texas ESBD", "--buyer", "Harris County",
            "--solicitation-number", "RFP 100",
            "--due-date", "2026-06-15",
        ]
        self._run(*argv2)
        argv3 = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "Texas ESBD", "--buyer", "City of Houston",
            "--solicitation-number", "IFB 200",
        ]
        self._run(*argv3)
        rc, out, _ = self._run("--active", str(self.active), "--archive", str(self.archive), "list")
        self.assertEqual(rc, 0)
        # Confirm ordering: 2026-06-15 row before 2026-07-01 row, blank last.
        idx_06 = out.index("2026-06-15")
        idx_07 = out.index("2026-07-01")
        idx_blank = out.index("city-of-houston")
        self.assertLess(idx_06, idx_07)
        self.assertLess(idx_07, idx_blank)

    def test_summary_counts(self) -> None:
        self._run(*self._base_add_args())
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "SAM.gov", "--buyer", "GSA",
            "--solicitation-number", "FA1234", "--status", "drafting",
        ]
        self._run(*argv)
        rc, out, _ = self._run("--active", str(self.active), "--archive", str(self.archive), "summary")
        self.assertEqual(rc, 0)
        self.assertIn("Total rows: 2", out)
        self.assertIn("watching", out)
        self.assertIn("drafting", out)
        self.assertIn("Texas ESBD", out)
        self.assertIn("SAM.gov", out)

    def test_score_text_strong_fit_lands_low_risk(self) -> None:
        score, risk, detail = pipeline.score_text(
            "Twin dormitory mattresses, box spring foundation, bed frame for residence hall"
        )
        # 7+ positive keyword hits at weight 25 clamps to 100.
        self.assertEqual(score, 100)
        self.assertEqual(risk, "low")
        self.assertEqual(detail["caution_hits"], 0)

    def test_score_text_terse_federal_title_lands_medium(self) -> None:
        # The kind of title SAM.gov actually returns: 1-2 keyword hits.
        score, risk, _ = pipeline.score_text("BED MATTRESS")
        # Single hit on "mattress" -> 25 -> medium band [25, 75).
        self.assertEqual(score, 25)
        self.assertEqual(risk, "medium")

        score2, risk2, _ = pipeline.score_text("Mattresses")
        # Two hits ("mattress" and "mattresses") -> 50 -> medium.
        self.assertEqual(score2, 50)
        self.assertEqual(risk2, "medium")

    def test_score_text_strong_caution_forces_high(self) -> None:
        score, risk, _ = pipeline.score_text(
            "Anti-ligature mattresses for behavioral health unit"
        )
        # 2 positive (mattress, mattresses) - 1 caution (anti-ligature) = 25,
        # but anti-ligature is STRONG_CAUTION → forced high regardless.
        self.assertEqual(risk, "high")

    def test_score_text_empty_input_is_high(self) -> None:
        score, risk, _ = pipeline.score_text("")
        self.assertEqual(score, 0)
        self.assertEqual(risk, "high")

    def test_score_text_aircraft_caution_drops_to_high(self) -> None:
        # Real SAM.gov example: "16--MATTRESS,AIRCRAFT" was a false-positive
        # match for an institutional mattress vendor. The 'aircraft' caution
        # offsets the single positive hit and parks it at high risk.
        score, risk, detail = pipeline.score_text("16--MATTRESS,AIRCRAFT")
        self.assertEqual(score, 0)  # 25 - 25 = 0
        self.assertEqual(risk, "high")
        self.assertGreaterEqual(detail["caution_hits"], 1)

    def test_score_text_concrete_caution_drops_to_high(self) -> None:
        # USACE "Casting Articulated Concrete Mattress" is an erosion-control
        # mat for waterways, not bedding. Concrete caution should catch it.
        score, risk, _ = pipeline.score_text(
            "2026 Casting Articulated Concrete Mattress"
        )
        self.assertEqual(score, 0)
        self.assertEqual(risk, "high")

    def test_score_text_inspection_services_caution(self) -> None:
        # VA wanted an inspector, not a manufacturer. We still surface as
        # medium because the hospital + mattress keywords compete with the
        # caution — operator triage is the right outcome.
        score, risk, _ = pipeline.score_text(
            "Hospital Grade Mattress Inspection Services"
        )
        # mattress + hospital positive = 50; inspection services caution = -25.
        self.assertEqual(score, 25)
        self.assertEqual(risk, "medium")

    def test_score_text_refurbishment_cautions(self) -> None:
        # Army Chinhae refurbishment row — refinish + reupholster cautions
        # plus an "overseas" geographic caution wipe out the positive hits.
        score, risk, _ = pipeline.score_text(
            "Repair, refinish, and reupholster furniture, sterilize mattresses overseas"
        )
        self.assertEqual(risk, "high")

    def test_score_updates_fit_score_and_risk(self) -> None:
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "Texas ESBD", "--buyer", "Harris County",
            "--solicitation-number", "RFP 100",
            "--title", "Twin mattresses, box spring, bed frame, cot, dormitory",
            "--primary-products", "mattresses, box spring, bed frame",
            "--commodity-terms", "mattress, bedding",
        ]
        self._run(*argv)
        _, rows_before = _read_csv(self.active)
        self.assertEqual(rows_before[0]["fit_score"], "")
        self.assertEqual(rows_before[0]["risk_level"], "")

        rc, _, _ = self._run("--active", str(self.active), "--archive", str(self.archive), "score")
        self.assertEqual(rc, 0)
        _, rows_after = _read_csv(self.active)
        self.assertNotEqual(rows_after[0]["fit_score"], "")
        self.assertNotEqual(rows_after[0]["risk_level"], "")
        self.assertIn(rows_after[0]["risk_level"], ("low", "medium", "high"))

    def test_score_dry_run_does_not_mutate(self) -> None:
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "Texas ESBD", "--buyer", "Harris County",
            "--solicitation-number", "RFP 100",
            "--title", "Twin mattresses",
        ]
        self._run(*argv)
        _, before = _read_csv(self.active)
        rc, out, _ = self._run("--active", str(self.active), "--archive", str(self.archive), "score", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("--dry-run", out)
        _, after = _read_csv(self.active)
        self.assertEqual(before, after)

    def test_move_to_archive(self) -> None:
        self._run(*self._base_add_args())
        rc, out, err = self._run(
            "--active", str(self.active),
            "--archive", str(self.archive),
            "move-to-archive",
            "texas-esbd-texas-facilities-commission-ifb-529-xyz",
        )
        self.assertEqual(rc, 0, err)
        _, active_rows = _read_csv(self.active)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(active_rows, [])
        self.assertEqual(len(archive_rows), 1)
        self.assertEqual(archive_rows[0]["opportunity_id"], "texas-esbd-texas-facilities-commission-ifb-529-xyz")

    def test_move_to_archive_unknown_id(self) -> None:
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "nope",
        )
        self.assertEqual(rc, 1)
        self.assertIn("not found", err)

    def test_move_to_archive_preserves_metadata_without_flags(self) -> None:
        # Regression: bare move-to-archive must not silently mutate the row.
        argv = self._base_add_args(
            status="watching",
            next_action="Triage and decide",
            notes="seed note",
            last_reviewed="2026-05-10",
        )
        self._run(*argv)
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
        )
        self.assertEqual(rc, 0, err)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(archive_rows[0]["status"], "watching")
        self.assertEqual(archive_rows[0]["next_action"], "Triage and decide")
        self.assertEqual(archive_rows[0]["notes"], "seed note")
        self.assertEqual(archive_rows[0]["last_reviewed"], "2026-05-10")

    def test_move_to_archive_sets_close_status(self) -> None:
        self._run(*self._base_add_args(next_action="Triage and decide", notes="seed"))
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
            "--status", "no-bid",
            "--next-action", "No-bid archived",
            "--note", "out of scope",
        )
        self.assertEqual(rc, 0, err)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(archive_rows[0]["status"], "no-bid")
        self.assertEqual(archive_rows[0]["next_action"], "No-bid archived")
        self.assertEqual(archive_rows[0]["notes"], "seed; out of scope")
        # last_reviewed bumps to today when metadata is changed.
        from datetime import datetime as _dt
        self.assertEqual(archive_rows[0]["last_reviewed"], _dt.now().date().isoformat())

    def test_move_to_archive_rejects_invalid_status(self) -> None:
        self._run(*self._base_add_args())
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
            "--status", "maybe",
        )
        self.assertEqual(rc, 1)
        self.assertIn("status", err)
        # Row must remain in active and not appear in archive.
        _, active_rows = _read_csv(self.active)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(len(active_rows), 1)
        self.assertEqual(archive_rows, [])

    def test_move_to_archive_note_sets_when_notes_empty(self) -> None:
        # Add a row with empty notes (default), then archive with --note.
        self._run(*self._base_add_args())
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
            "--note", "first note",
        )
        self.assertEqual(rc, 0, err)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(archive_rows[0]["notes"], "first note")

    def test_move_to_archive_next_action_can_clear(self) -> None:
        # Passing --next-action "" explicitly clears the field.
        self._run(*self._base_add_args(next_action="Triage and decide"))
        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
            "--next-action", "",
        )
        self.assertEqual(rc, 0, err)
        _, archive_rows = _read_csv(self.archive)
        self.assertEqual(archive_rows[0]["next_action"], "")


if __name__ == "__main__":
    unittest.main()
