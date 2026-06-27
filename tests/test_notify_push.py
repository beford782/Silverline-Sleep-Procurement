"""Unit tests for tools/notify_push.py. Stdlib unittest, no network."""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import notify_push  # noqa: E402
import pipeline  # noqa: E402
import lead_radar  # noqa: E402


def _active_row(**kw) -> dict:
    row = {k: "" for k in pipeline.CANONICAL_HEADER}
    row.update(kw)
    return row


def _lead_row(**kw) -> dict:
    row = {k: "" for k in lead_radar.LEAD_HEADER} if hasattr(lead_radar, "LEAD_HEADER") else {}
    row.update(kw)
    return row


class SelectRowsTests(unittest.TestCase):
    def test_selects_only_rows_for_the_date(self) -> None:
        active = [
            _active_row(opportunity_id="a", title="Mattresses", created_date="2026-06-27"),
            _active_row(opportunity_id="b", title="Old", created_date="2026-06-20"),
        ]
        leads = [_lead_row(lead_id="L1", title="Furniture", created_date="2026-06-27")]
        accepts, sel_leads = notify_push.select_new_rows(active, leads, "2026-06-27")
        self.assertEqual([r["opportunity_id"] for r in accepts], ["a"])
        self.assertEqual([r["lead_id"] for r in sel_leads], ["L1"])


class BuildEmailTests(unittest.TestCase):
    def test_subject_and_body_reflect_counts(self) -> None:
        accepts = [_active_row(opportunity_id="a", title="Correctional Mattresses",
                               source="Bonfire", due_date="2026-07-10",
                               portal_url="https://x/opp/1", fit_score="90")]
        leads = [_lead_row(lead_id="L1", title="School Furniture", source="IonWave",
                           due_date="2026-08-01", fit_score="35")]
        subject, body = notify_push.build_email(accepts, leads, "https://gh/pr/9", "2026-06-27")
        self.assertIn("1 bid fit", subject)
        self.assertIn("1 lead", subject)
        self.assertIn("Correctional Mattresses", body)
        self.assertIn("ACTIVE BID FITS", body)
        self.assertIn("LEAD RADAR", body)
        self.assertIn("https://x/opp/1", body)
        self.assertIn("https://gh/pr/9", body)

    def test_accepts_only_omits_lead_section(self) -> None:
        accepts = [_active_row(opportunity_id="a", title="Mattresses", created_date="2026-06-27")]
        subject, body = notify_push.build_email(accepts, [], "", "2026-06-27")
        self.assertIn("1 bid fit", subject)
        self.assertNotIn("LEAD RADAR", body)


class MainDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.leads = self.tmp / "leads.csv"

    def _run(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = notify_push.main(list(argv))
        return rc, out.getvalue()

    def test_dry_run_prints_email_for_new_rows(self) -> None:
        pipeline.write_rows_atomic(self.active, [
            _active_row(opportunity_id="a", title="Jail Mattresses", source="Bonfire",
                        created_date="2026-06-27"),
        ])
        lead_radar.write_lead_rows_atomic(self.leads, [
            lead_radar.build_lead_row(
                _active_row(opportunity_id="x", title="Office Furniture", source="IonWave",
                            created_date="2026-06-27"),
                None, "2026-06-27"),
        ])
        rc, out = self._run("--active", str(self.active), "--leads", str(self.leads),
                            "--created-date", "2026-06-27", "--pr-url", "https://gh/pr/5",
                            "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)
        self.assertIn("Jail Mattresses", out)
        self.assertIn("https://gh/pr/5", out)

    def test_no_new_rows_sends_nothing(self) -> None:
        pipeline.write_rows_atomic(self.active, [
            _active_row(opportunity_id="a", title="Old", created_date="2026-01-01"),
        ])
        rc, out = self._run("--active", str(self.active), "--leads", str(self.leads),
                            "--created-date", "2026-06-27", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("nothing new", out)

    def test_failure_mode_dry_run(self) -> None:
        rc, out = self._run("--failure", "--run-url", "https://gh/run/9",
                            "--created-date", "2026-06-27", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("PIPELINE FAILED", out)
        self.assertIn("https://gh/run/9", out)


if __name__ == "__main__":
    unittest.main()
