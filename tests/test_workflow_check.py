"""Unit tests for tools/workflow_check.py. Stdlib unittest, tempfile-backed."""

from __future__ import annotations

import csv
import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pipeline  # noqa: E402
import workflow_check  # noqa: E402


def _write_pipeline(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            full = {k: "" for k in pipeline.CANONICAL_HEADER}
            full.update(row)
            writer.writerow(full)


def _row(opportunity_id: str, status: str, **overrides: str) -> dict:
    row = {
        "opportunity_id": opportunity_id,
        "status": status,
        "source": "Test Portal",
        "buyer": "Test Buyer",
        "solicitation_number": opportunity_id.upper(),
        "title": f"Title {opportunity_id}",
        "due_date": "2026-06-15",
        "next_action": "Review",
        "owner": "Ops",
        "last_reviewed": "2026-06-01",
    }
    row.update(overrides)
    return row


class WorkflowCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active_csv = self.tmp / "bids" / "active" / "_pipeline.csv"
        self.archive_csv = self.tmp / "bids" / "archive" / "_pipeline_archive.csv"
        self.active_dir = self.tmp / "bids" / "active"
        self.archive_dir = self.tmp / "bids" / "archive"
        # Hermetic lead/demand paths (absent => empty) so CLI tests do not read
        # the repo's real Lead/Demand Radar CSVs via the new defaults.
        self.leads_csv = self.tmp / "leads.csv"
        self.demand_csv = self.tmp / "demand.csv"

    def _findings(self, **kwargs) -> list[workflow_check.Finding]:
        return workflow_check.check_workflow(
            active_path=self.active_csv,
            archive_path=self.archive_csv,
            active_dir=self.active_dir,
            archive_dir=self.archive_dir,
            today=kwargs.pop("today", date(2026, 6, 1)),
            stale_days=kwargs.pop("stale_days", 14),
            require_active_markdown=kwargs.pop("require_active_markdown", False),
        )

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = workflow_check.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def test_clean_active_and_archive_pass(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [_row("archive-one", "awarded")])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")
        (self.archive_dir / "archive-one.md").write_text("| Status | awarded |\n", encoding="utf-8")

        findings = self._findings()
        self.assertEqual(findings, [])

    def test_markdown_status_mismatch_is_error(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | watching |\n", encoding="utf-8")

        findings = self._findings()
        self.assertIn("status-mismatch", {f.code for f in findings})
        self.assertTrue(any(f.severity == "ERROR" for f in findings))

    def test_drafting_row_missing_active_markdown_is_error(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])

        findings = self._findings()
        self.assertIn("missing-active-md", {f.code for f in findings})

    def test_watching_row_missing_active_markdown_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "watching")])
        _write_pipeline(self.archive_csv, [])

        findings = self._findings()
        by_code = {f.code: f for f in findings}
        self.assertEqual(by_code["missing-watch-md"].severity, "WARN")

    def test_active_closed_status_is_error(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "no-bid")])
        _write_pipeline(self.archive_csv, [])

        findings = self._findings()
        self.assertIn("closed-status-in-active", {f.code for f in findings})

    def test_no_bid_without_memo_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [])
        _write_pipeline(self.archive_csv, [_row("closed-one", "no-bid")])

        findings = self._findings()
        by_code = {f.code: f for f in findings}
        self.assertEqual(by_code["missing-no-bid-memo"].severity, "WARN")

    def test_no_bid_memo_satisfies_archive_markdown(self) -> None:
        _write_pipeline(self.active_csv, [])
        _write_pipeline(self.archive_csv, [_row("closed-one", "no-bid")])
        (self.archive_dir / "closed-one_no_bid.md").write_text("# No-bid\n", encoding="utf-8")

        findings = self._findings()
        self.assertNotIn("missing-no-bid-memo", {f.code for f in findings})

    def test_active_and_archive_duplicate_is_error(self) -> None:
        _write_pipeline(self.active_csv, [_row("same-id", "watching")])
        _write_pipeline(self.archive_csv, [_row("same-id", "awarded")])

        findings = self._findings()
        self.assertIn("active-archive-duplicate", {f.code for f in findings})

    def test_stale_last_reviewed_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "watching", last_reviewed="2026-05-01")])
        _write_pipeline(self.archive_csv, [])

        findings = self._findings(today=date(2026, 6, 1), stale_days=14)
        by_code = {f.code: f for f in findings}
        self.assertEqual(by_code["stale-review"].severity, "WARN")

    def test_biddable_row_with_blocker_is_error(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "drafting", compliance_blocker="SAM not Active")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")

        findings = self._findings()
        by_code = {f.code: f for f in findings}
        self.assertIn("biddable-with-open-blocker", by_code)
        self.assertEqual(by_code["biddable-with-open-blocker"].severity, "ERROR")

    def test_watching_row_with_blocker_is_silent(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "watching", compliance_blocker="SAM not Active",
                 procurement_risk="blocker", gate_status="blocked")])
        _write_pipeline(self.archive_csv, [])

        findings = self._findings()
        self.assertNotIn("biddable-with-open-blocker", {f.code for f in findings})

    def test_biddable_row_without_blocker_is_silent(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "drafting", gate_status="bid_ready")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")

        findings = self._findings()
        self.assertNotIn("biddable-with-open-blocker", {f.code for f in findings})

    def test_orphan_markdown_is_error(self) -> None:
        _write_pipeline(self.active_csv, [])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "orphan.md").write_text("| Status | watching |\n", encoding="utf-8")

        findings = self._findings()
        self.assertIn("orphan-active-md", {f.code for f in findings})

    # ---- FIX 5: CSV data-integrity checks (all WARN) -------------------------
    def test_future_posted_date_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "watching", posted_date="2027-01-01")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 6, 1))
        fut = [f for f in findings if f.code == "future-date"]
        self.assertTrue(fut)
        self.assertTrue(all(f.severity == "WARN" for f in fut))

    def test_future_due_date_is_not_flagged(self) -> None:
        # due_date is a deadline; a future value is normal and must NOT warn.
        _write_pipeline(self.active_csv, [_row("active-one", "watching", due_date="2027-01-01")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 6, 1))
        self.assertNotIn("future-date", {f.code for f in findings})

    def test_posted_after_due_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "watching", posted_date="2026-06-20", due_date="2026-06-05")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 7, 1))
        by_code = {f.code: f for f in findings}
        self.assertIn("date-inversion", by_code)
        self.assertEqual(by_code["date-inversion"].severity, "WARN")

    def test_score_out_of_range_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "watching", fit_score="150", win_score="-3")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 6, 1))
        oor = [f for f in findings if f.code == "score-out-of-range"]
        self.assertEqual(len(oor), 2)  # fit_score=150 and win_score=-3
        self.assertTrue(all(f.severity == "WARN" for f in oor))

    def test_non_numeric_score_is_warning(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "watching", fit_score="high")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 6, 1))
        self.assertIn("score-not-numeric", {f.code for f in findings})

    def test_valid_scores_and_dates_have_no_integrity_warnings(self) -> None:
        _write_pipeline(self.active_csv, [
            _row("active-one", "watching", posted_date="2026-05-01", due_date="2026-06-15",
                 fit_score="80", win_score="55", last_reviewed="2026-06-28")])
        _write_pipeline(self.archive_csv, [])
        findings = self._findings(today=date(2026, 7, 1))
        codes = {f.code for f in findings}
        for code in ("future-date", "date-inversion", "score-out-of-range", "score-not-numeric"):
            self.assertNotIn(code, codes)

    def test_lead_radar_integrity_is_checked(self) -> None:
        leads = self.tmp / "leads.csv"
        with leads.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh, fieldnames=["lead_id", "title", "posted_date", "due_date", "fit_score"],
                lineterminator="\n")
            writer.writeheader()
            writer.writerow({"lead_id": "L1", "title": "Some lead",
                             "posted_date": "2027-01-01", "due_date": "", "fit_score": "200"})
        _write_pipeline(self.active_csv, [])
        _write_pipeline(self.archive_csv, [])
        findings = workflow_check.check_workflow(
            active_path=self.active_csv, archive_path=self.archive_csv,
            active_dir=self.active_dir, archive_dir=self.archive_dir,
            today=date(2026, 6, 1), stale_days=14,
            leads_path=leads, demand_path=None)
        codes = {f.code for f in findings}
        self.assertIn("future-date", codes)
        self.assertIn("score-out-of-range", codes)
        self.assertTrue(any("Lead Radar" in f.message for f in findings))

    def test_cli_success(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")

        rc, out, err = self._run(
            "--active", str(self.active_csv),
            "--archive", str(self.archive_csv),
            "--active-dir", str(self.active_dir),
            "--archive-dir", str(self.archive_dir),
            "--leads", str(self.leads_csv),
            "--demand", str(self.demand_csv),
            "--today", "2026-06-01",
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("OK", out)

    def test_cli_errors_fail(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])

        rc, out, err = self._run(
            "--active", str(self.active_csv),
            "--archive", str(self.archive_csv),
            "--active-dir", str(self.active_dir),
            "--archive-dir", str(self.archive_dir),
            "--leads", str(self.leads_csv),
            "--demand", str(self.demand_csv),
            "--today", "2026-06-01",
        )
        self.assertEqual(rc, 1, err)
        self.assertIn("missing-active-md", out)

    def test_cli_warnings_pass_unless_requested(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "watching")])
        _write_pipeline(self.archive_csv, [])

        base = [
            "--active", str(self.active_csv),
            "--archive", str(self.archive_csv),
            "--active-dir", str(self.active_dir),
            "--archive-dir", str(self.archive_dir),
            "--leads", str(self.leads_csv),
            "--demand", str(self.demand_csv),
            "--today", "2026-06-01",
        ]
        rc, out, err = self._run(*base)
        self.assertEqual(rc, 0, err)
        self.assertIn("warning", out.lower())

        rc2, out2, err2 = self._run(*base, "--fail-on-warnings")
        self.assertEqual(rc2, 1, err2)
        self.assertIn("missing-watch-md", out2)


if __name__ == "__main__":
    unittest.main()
