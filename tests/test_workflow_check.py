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

    def test_orphan_markdown_is_error(self) -> None:
        _write_pipeline(self.active_csv, [])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "orphan.md").write_text("| Status | watching |\n", encoding="utf-8")

        findings = self._findings()
        self.assertIn("orphan-active-md", {f.code for f in findings})

    def test_capability_statement_companion_is_not_orphan(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")
        (self.active_dir / "active-one_capability_statement.md").write_text(
            "# Capability Statement\n", encoding="utf-8"
        )

        findings = self._findings()
        self.assertNotIn("orphan-active-md", {f.code for f in findings})

    def test_cli_success(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "drafting")])
        _write_pipeline(self.archive_csv, [])
        (self.active_dir / "active-one.md").write_text("| Status | drafting |\n", encoding="utf-8")

        rc, out, err = self._run(
            "--active", str(self.active_csv),
            "--archive", str(self.archive_csv),
            "--active-dir", str(self.active_dir),
            "--archive-dir", str(self.archive_dir),
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
