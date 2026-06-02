"""Unit tests for tools/dashboard.py. Stdlib unittest, tempfile-backed."""

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

import dashboard  # noqa: E402
import pipeline  # noqa: E402


def _write_pipeline(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            full = {k: "" for k in pipeline.CANONICAL_HEADER}
            full.update(row)
            writer.writerow(full)


def _row(opportunity_id: str, **overrides: str) -> dict:
    row = {
        "opportunity_id": opportunity_id,
        "status": "watching",
        "source": "Test Portal",
        "buyer": "Test Buyer",
        "solicitation_number": opportunity_id.upper(),
        "title": f"Title {opportunity_id}",
        "due_date": "2026-06-10",
        "question_deadline": "2026-06-05",
        "fit_score": "75",
        "risk_level": "low",
        "next_action": "Review",
        "owner": "Ops",
        "last_reviewed": "2026-06-01",
    }
    row.update(overrides)
    return row


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.active_dir = self.tmp / "bids" / "active"
        self.draft_dir = self.tmp / "build" / "drafts"
        self.active_dir.mkdir(parents=True)
        self.draft_dir.mkdir(parents=True)

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = dashboard.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def _base_args(self) -> list[str]:
        return [
            "--active", str(self.active),
            "--active-dir", str(self.active_dir),
            "--draft-dir", str(self.draft_dir),
            "--today", "2026-06-02",
        ]

    def test_render_includes_deadlines_and_summary(self) -> None:
        rows = [
            _row("due-soon", due_date="2026-06-03"),
            _row("past-due", due_date="2026-05-30"),
        ]
        body = dashboard.render_dashboard(
            rows,
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="all",
        )
        self.assertIn("Pipeline dashboard - 2026-06-02", body)
        self.assertIn("active rows: 2", body)
        self.assertIn("+1d 2026-06-03", body)
        self.assertIn("OVERDUE 3d 2026-05-30", body)

    def test_render_q_and_a_deadline(self) -> None:
        body = dashboard.render_dashboard(
            [_row("qa-today", question_deadline="2026-06-02")],
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="deadlines",
        )
        self.assertIn("Q&A deadlines", body)
        self.assertIn("TODAY 2026-06-02", body)

    def test_render_hygiene_gaps(self) -> None:
        body = dashboard.render_dashboard(
            [_row("messy", owner="", next_action="", last_reviewed="2026-05-01")],
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="hygiene",
        )
        self.assertIn("owner, next_action", body)
        self.assertIn("32d since review", body)

    def test_render_risk_gaps(self) -> None:
        body = dashboard.render_dashboard(
            [
                _row("needs-score", fit_score="", risk_level=""),
                _row("high-risk", fit_score="0", risk_level="high"),
            ],
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="risk",
        )
        self.assertIn("Needs scoring", body)
        self.assertIn("needs-score", body)
        self.assertIn("High risk", body)
        self.assertIn("high-risk", body)

    def test_render_drafts_ready_to_promote(self) -> None:
        (self.draft_dir / "ready-one_draft.md").write_text("# Ready\n", encoding="utf-8")
        body = dashboard.render_dashboard(
            [_row("ready-one")],
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="drafts",
        )
        self.assertIn("Drafts ready to promote", body)
        self.assertIn("python tools/promote_draft.py ready-one", body)

    def test_existing_active_markdown_suppresses_promote_suggestion(self) -> None:
        (self.draft_dir / "ready-one_draft.md").write_text("# Ready\n", encoding="utf-8")
        (self.active_dir / "ready-one.md").write_text("# Active\n", encoding="utf-8")
        body = dashboard.render_dashboard(
            [_row("ready-one")],
            today=date(2026, 6, 2),
            days=14,
            stale_days=14,
            draft_dir=self.draft_dir,
            active_dir=self.active_dir,
            show="drafts",
        )
        self.assertIn("(none)", body)

    def test_cli_happy_path(self) -> None:
        _write_pipeline(self.active, [_row("one")])
        rc, out, err = self._run(*self._base_args())
        self.assertEqual(rc, 0, err)
        self.assertIn("Pipeline dashboard", out)
        self.assertIn("one", out)

    def test_cli_show_summary_only(self) -> None:
        _write_pipeline(self.active, [_row("one")])
        rc, out, err = self._run(*self._base_args(), "--show", "summary")
        self.assertEqual(rc, 0, err)
        self.assertIn("Summary", out)
        self.assertNotIn("Response deadlines", out)

    def test_cli_negative_days_rejected(self) -> None:
        _write_pipeline(self.active, [])
        rc, _, err = self._run(*self._base_args(), "--days", "-1")
        self.assertEqual(rc, 2)
        self.assertIn("--days", err)

    def test_cli_missing_pipeline_errors(self) -> None:
        rc, _, err = self._run(*self._base_args())
        self.assertEqual(rc, 1)
        self.assertIn("pipeline file not found", err)


if __name__ == "__main__":
    unittest.main()
