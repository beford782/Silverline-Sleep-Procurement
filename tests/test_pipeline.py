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
from unittest import mock

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

    def test_canonical_header_appends_win_columns(self) -> None:
        # The Win Engine appends win_score/win_factors to the END (prefix-safe).
        self.assertEqual(pipeline.CANONICAL_HEADER[-2:], ["win_score", "win_factors"])

    def test_read_rows_accepts_legacy_24col_header(self) -> None:
        # The critical backward-compat test: a legacy 24-column pipeline CSV
        # (everything up to compliance_blocker, before win_score/win_factors)
        # still read_rows-loads after CANONICAL_HEADER grows.
        legacy_24 = pipeline.CANONICAL_HEADER[:24]
        self.assertEqual(legacy_24[-1], "compliance_blocker")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy24.csv"
            with path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=legacy_24, lineterminator="\n")
                writer.writeheader()
                writer.writerow({"opportunity_id": "legacy-24", "status": "watching",
                                 "source": "Legacy", "buyer": "Buyer", "title": "Mattresses"})
            header, rows = pipeline.read_rows(path)
        self.assertEqual(header, legacy_24)
        self.assertEqual(rows[0]["opportunity_id"], "legacy-24")
        self.assertEqual(rows[0]["win_score"], "")
        self.assertEqual(rows[0]["win_factors"], "")

    def test_read_rows_accepts_legacy_header_and_fills_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "legacy.csv"
            legacy_header = pipeline.CANONICAL_HEADER[:-3]
            with path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(fh, fieldnames=legacy_header, lineterminator="\n")
                writer.writeheader()
                writer.writerow({
                    "opportunity_id": "legacy-one",
                    "status": "watching",
                    "source": "Legacy",
                    "buyer": "Buyer",
                    "title": "Mattresses",
                })

            header, rows = pipeline.read_rows(path)
        self.assertEqual(header, legacy_header)
        self.assertEqual(rows[0]["opportunity_id"], "legacy-one")
        self.assertEqual(rows[0]["procurement_risk"], "")
        self.assertEqual(rows[0]["gate_status"], "")
        self.assertEqual(rows[0]["compliance_blocker"], "")


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

    def test_invalid_risk_level_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(risk_level="maybe"))
        self.assertEqual(rc, 1)
        self.assertIn("risk_level", err)
        _, rows = _read_csv(self.active)
        self.assertEqual(rows, [])

    def test_procurement_gate_fields_are_validated_and_written(self) -> None:
        rc, _, err = self._run(*self._base_add_args(
            procurement_risk="blocker",
            gate_status="blocked",
            compliance_blocker="sam_registration_pending; specs_pending",
        ))
        self.assertEqual(rc, 0, err)
        _, rows = _read_csv(self.active)
        self.assertEqual(rows[0]["procurement_risk"], "blocker")
        self.assertEqual(rows[0]["gate_status"], "blocked")
        self.assertEqual(rows[0]["compliance_blocker"], "sam_registration_pending; specs_pending")

    def test_invalid_procurement_risk_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(procurement_risk="maybe"))
        self.assertEqual(rc, 1)
        self.assertIn("procurement_risk", err)

    def test_invalid_gate_status_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(gate_status="maybe"))
        self.assertEqual(rc, 1)
        self.assertIn("gate_status", err)

    def test_invalid_fit_score_is_rejected(self) -> None:
        rc, _, err = self._run(*self._base_add_args(fit_score="101"))
        self.assertEqual(rc, 1)
        self.assertIn("fit_score", err)
        _, rows = _read_csv(self.active)
        self.assertEqual(rows, [])

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
        rc, out, _ = self._run("--active", str(self.active), "--archive", str(self.archive),
                               "list", "--sort", "due")
        self.assertEqual(rc, 0)
        # Confirm ordering: 2026-06-15 row before 2026-07-01 row, blank last.
        idx_06 = out.index("2026-06-15")
        idx_07 = out.index("2026-07-01")
        idx_blank = out.index("city-of-houston")
        self.assertLess(idx_06, idx_07)
        self.assertLess(idx_07, idx_blank)

    def test_list_default_sort_is_win_score_desc(self) -> None:
        # Two rows with explicit win_score; the higher must list first under the
        # new default (--sort win). Lower win_score sinks regardless of due date.
        self._run(*self._base_add_args(
            opportunity_id="low-win", title="Mattresses", due_date="2026-06-15"))
        self._run(*self._base_add_args(
            opportunity_id="high-win", title="Mattresses", due_date="2026-12-31"))
        # Stamp win_score directly via the CSV (simpler than a full compute here).
        header, rows = pipeline.read_rows(self.active)
        for r in rows:
            r["win_score"] = "90" if r["opportunity_id"] == "high-win" else "10"
        pipeline.write_rows_atomic(self.active, rows)

        rc, out, _ = self._run("--active", str(self.active), "--archive", str(self.archive), "list")
        self.assertEqual(rc, 0)
        self.assertLess(out.index("high-win"), out.index("low-win"))

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
        # A clear, multi-term mattress title is a strong ACCEPT -> low risk.
        score, risk, detail = pipeline.score_text(
            "Twin dormitory mattresses, box spring foundation, bed frame for residence hall"
        )
        self.assertGreaterEqual(score, 75)
        self.assertEqual(risk, "low")
        self.assertEqual(detail["decision"], "ACCEPT")

    def test_score_text_delegates_fit_score_to_relevance(self) -> None:
        # fit_score is the relevance confidence, not the retired substring math:
        # a plain "Mattresses" title is a strong ACCEPT/low, where the old
        # scorer parked it at 50/medium.
        score, risk, detail = pipeline.score_text("Mattresses")
        self.assertGreaterEqual(score, 75)
        self.assertEqual(risk, "low")
        self.assertEqual(detail["decision"], "ACCEPT")

    def test_score_text_no_substring_false_fire(self) -> None:
        # The retired scorer counted "cot" inside "Scott" and "foundation"
        # inside "foundational"; whole-word relevance does not.
        score, risk, detail = pipeline.score_text(
            "Scott County foundational paving services"
        )
        self.assertEqual(score, 0)
        self.assertEqual(risk, "high")
        self.assertEqual(detail["decision"], "REJECT")

    def test_score_text_anti_ligature_not_penalized(self) -> None:
        # anti-ligature is a premium correctional feature now -> ACCEPT/low,
        # not the retired scorer's forced-high caution.
        score, risk, _ = pipeline.score_text(
            "Anti-ligature mattresses for behavioral health unit"
        )
        self.assertGreaterEqual(score, 75)
        self.assertEqual(risk, "low")

    def test_score_text_empty_input_is_high(self) -> None:
        score, risk, _ = pipeline.score_text("")
        self.assertEqual(score, 0)
        self.assertEqual(risk, "high")

    def test_score_text_unambiguous_exclude_is_high(self) -> None:
        # "Articulated concrete mattress" (erosion mat) is an unambiguous
        # hard-exclude -> REJECT/high.
        score, risk, detail = pipeline.score_text(
            "2026 Casting Articulated Concrete Mattress"
        )
        self.assertLess(score, 25)
        self.assertEqual(risk, "high")
        self.assertEqual(detail["decision"], "REJECT")

    def test_score_text_context_collision_demoted_to_medium(self) -> None:
        # "aircraft" alongside a strong mattress term demotes to REVIEW (medium)
        # instead of silently rejecting — the DLA Aviation false-negative fix.
        score, risk, detail = pipeline.score_text("16--MATTRESS,AIRCRAFT")
        self.assertEqual(risk, "medium")
        self.assertEqual(detail["decision"], "REVIEW")

    def test_score_updates_fit_score_and_fills_blank_risk(self) -> None:
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

    def test_score_preserves_existing_risk_level_by_default(self) -> None:
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "SAM.gov", "--buyer", "Air Force",
            "--solicitation-number", "FA-100",
            "--title", "Twin mattresses, box spring, bed frame, cot, dormitory",
            "--primary-products", "mattresses, box spring, bed frame",
            "--commodity-terms", "mattress, bedding",
            "--risk-level", "high",
        ]
        self._run(*argv)

        rc, _, err = self._run("--active", str(self.active), "--archive", str(self.archive), "score")
        self.assertEqual(rc, 0, err)
        _, rows_after = _read_csv(self.active)
        self.assertEqual(rows_after[0]["fit_score"], "95")
        self.assertEqual(rows_after[0]["risk_level"], "high")

    def test_score_overwrite_risk_flag_replaces_existing_risk_level(self) -> None:
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "SAM.gov", "--buyer", "Air Force",
            "--solicitation-number", "FA-101",
            "--title", "Twin mattresses, box spring, bed frame, cot, dormitory",
            "--primary-products", "mattresses, box spring, bed frame",
            "--commodity-terms", "mattress, bedding",
            "--risk-level", "high",
        ]
        self._run(*argv)

        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "score", "--overwrite-risk",
        )
        self.assertEqual(rc, 0, err)
        _, rows_after = _read_csv(self.active)
        self.assertEqual(rows_after[0]["fit_score"], "95")
        self.assertEqual(rows_after[0]["risk_level"], "low")

    def test_score_ignores_operator_notes(self) -> None:
        argv = [
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "SAM.gov", "--buyer", "Air Force",
            "--solicitation-number", "FA-102",
            "--title", "Mattresses",
            "--notes", (
                "Procurement caution: SAM registration pending, aircraft base access, "
                "liquidated damages, nationwide delivery, overseas delivery."
            ),
        ]
        self._run(*argv)

        rc, _, err = self._run("--active", str(self.active), "--archive", str(self.archive), "score")
        self.assertEqual(rc, 0, err)
        _, rows_after = _read_csv(self.active)
        self.assertEqual(rows_after[0]["fit_score"], "80")
        self.assertEqual(rows_after[0]["risk_level"], "low")

    def test_score_only_created_date_limits_updates(self) -> None:
        old_row = self._base_add_args(
            opportunity_id="old-row",
            title="Mattresses",
            created_date="2026-06-24",
            last_reviewed="2026-06-24",
        )
        new_row = self._base_add_args(
            opportunity_id="new-row",
            title="Mattresses",
            created_date="2026-06-25",
            last_reviewed="2026-06-25",
        )
        self._run(*old_row)
        self._run(*new_row)

        rc, _, err = self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "score", "--only-created-date", "2026-06-25",
        )
        self.assertEqual(rc, 0, err)
        _, rows_after = _read_csv(self.active)
        by_id = {r["opportunity_id"]: r for r in rows_after}
        self.assertEqual(by_id["old-row"]["fit_score"], "")
        self.assertEqual(by_id["old-row"]["risk_level"], "")
        self.assertEqual(by_id["old-row"]["last_reviewed"], "2026-06-24")
        self.assertEqual(by_id["new-row"]["fit_score"], "80")
        self.assertEqual(by_id["new-row"]["risk_level"], "low")

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

    def test_move_to_archive_keeps_active_when_archive_write_fails(self) -> None:
        self._run(*self._base_add_args())
        original_write = pipeline.write_rows_atomic

        def fail_archive_write(path: Path, rows) -> None:
            if path == self.archive:
                raise OSError("synthetic archive failure")
            original_write(path, rows)

        with mock.patch.object(pipeline, "write_rows_atomic", side_effect=fail_archive_write):
            rc, _, err = self._run(
                "--active", str(self.active), "--archive", str(self.archive),
                "move-to-archive", "texas-esbd-texas-facilities-commission-ifb-529-xyz",
            )
        self.assertEqual(rc, 1)
        self.assertIn("synthetic archive failure", err)
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


class WinScoreCommandTests(unittest.TestCase):
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

    def _add_mattress_row(self) -> None:
        self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--source", "Texas ESBD", "--buyer", "Harris County, TX",
            "--solicitation-number", "RFP 100",
            "--title", "Correctional mattresses for county jail",
            "--primary-products", "mattresses",
            "--estimated-value", "200000",
            "--due-date", "2026-12-31",
        )

    def test_win_score_dry_run_writes_nothing(self) -> None:
        self._add_mattress_row()
        _, before = _read_csv(self.active)
        rc, out, err = self._run("--active", str(self.active), "--archive", str(self.archive),
                                 "win-score", "--dry-run")
        self.assertEqual(rc, 0, err)
        self.assertIn("--dry-run", out)
        _, after = _read_csv(self.active)
        self.assertEqual(before, after)

    def test_win_score_real_run_round_trips(self) -> None:
        self._add_mattress_row()
        rc, _, err = self._run("--active", str(self.active), "--archive", str(self.archive),
                               "win-score")
        self.assertEqual(rc, 0, err)
        # Round-trips through read_rows/write_rows_atomic and parses.
        _, rows = pipeline.read_rows(self.active)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["win_score"])
        self.assertGreater(int(rows[0]["win_score"]), 0)
        # win_factors parses as the compact pf=..;vt=..;wp=..;sf=.. form.
        factors = dict(kv.split("=") for kv in rows[0]["win_factors"].split(";"))
        self.assertEqual(set(factors), {"pf", "vt", "wp", "sf"})
        for v in factors.values():
            float(v)  # each value parses as a float

    def test_win_score_only_created_date_limits_updates(self) -> None:
        self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--opportunity-id", "old", "--source", "Texas ESBD",
            "--buyer", "Harris County, TX", "--solicitation-number", "A",
            "--title", "Mattresses", "--created-date", "2026-06-24",
        )
        self._run(
            "--active", str(self.active), "--archive", str(self.archive),
            "add", "--opportunity-id", "new", "--source", "Texas ESBD",
            "--buyer", "Harris County, TX", "--solicitation-number", "B",
            "--title", "Mattresses", "--created-date", "2026-06-25",
        )
        rc, _, err = self._run("--active", str(self.active), "--archive", str(self.archive),
                               "win-score", "--only-created-date", "2026-06-25")
        self.assertEqual(rc, 0, err)
        _, rows = pipeline.read_rows(self.active)
        by_id = {r["opportunity_id"]: r for r in rows}
        self.assertEqual(by_id["old"]["win_score"], "")
        self.assertTrue(by_id["new"]["win_score"])


if __name__ == "__main__":
    unittest.main()
