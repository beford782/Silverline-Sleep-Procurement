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
import demand_radar  # noqa: E402


def _active_row(**kw) -> dict:
    row = {k: "" for k in pipeline.CANONICAL_HEADER}
    row.update(kw)
    return row


def _lead_row(**kw) -> dict:
    row = {k: "" for k in lead_radar.LEAD_HEADER} if hasattr(lead_radar, "LEAD_HEADER") else {}
    row.update(kw)
    return row


def _demand_row(**kw) -> dict:
    row = {k: "" for k in demand_radar.DEMAND_HEADER}
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


class DemandSectionTests(unittest.TestCase):
    def test_select_new_demand_uses_first_seen(self) -> None:
        rows = [
            _demand_row(demand_id="d-new", segment="hotel", first_seen="2026-06-27"),
            _demand_row(demand_id="d-old", segment="hotel", first_seen="2026-06-01"),
        ]
        sel = notify_push.select_new_demand_rows(rows, "2026-06-27")
        self.assertEqual([r["demand_id"] for r in sel], ["d-new"])

    def test_demand_section_appears_and_subject_counts(self) -> None:
        demand = [_demand_row(demand_id="d1", segment="senior-living", scale="120 beds",
                              est_buy_window="2026-09", location="TX",
                              facility_name="Cedar Park Senior Living",
                              source_url="https://news/x", first_seen="2026-06-27")]
        subject, body = notify_push.build_email([], [], "", "2026-06-27", demand)
        self.assertIn("1 demand", subject)
        self.assertIn("DEMAND RADAR", body)
        self.assertIn("Cedar Park Senior Living", body)
        self.assertIn("2026-09", body)
        self.assertIn("https://news/x", body)

    def test_demand_lines_sorted_by_window_blanks_last(self) -> None:
        demand = [
            _demand_row(demand_id="late", facility_name="Late", est_buy_window="2027-01"),
            _demand_row(demand_id="blank", facility_name="Blank", est_buy_window=""),
            _demand_row(demand_id="soon", facility_name="Soon", est_buy_window="2026-08"),
        ]
        _, body = notify_push.build_email([], [], "", "2026-06-27", demand)
        i_soon = body.index("Soon")
        i_late = body.index("Late")
        i_blank = body.index("Blank")
        self.assertLess(i_soon, i_late)
        self.assertLess(i_late, i_blank)

    def test_no_demand_no_section(self) -> None:
        accepts = [_active_row(opportunity_id="a", title="Mattresses", created_date="2026-06-27")]
        subject, body = notify_push.build_email(accepts, [], "", "2026-06-27")
        self.assertNotIn("DEMAND RADAR", body)
        self.assertNotIn("demand", subject)

    def test_demand_never_under_bid_fits_heading(self) -> None:
        accepts = [_active_row(opportunity_id="a", title="Jail Mattresses",
                               created_date="2026-06-27")]
        demand = [_demand_row(demand_id="d1", segment="hotel", facility_name="Grand Hotel",
                              est_buy_window="2026-09", first_seen="2026-06-27")]
        _, body = notify_push.build_email(accepts, [], "", "2026-06-27", demand)
        # The demand facility must fall AFTER the demand heading and never inside
        # the ACTIVE BID FITS block.
        bid_heading = body.index("ACTIVE BID FITS")
        demand_heading = body.index("DEMAND RADAR")
        self.assertLess(bid_heading, demand_heading)
        self.assertGreater(body.index("Grand Hotel"), demand_heading)
        # The bid block (between its heading and the demand heading) must not name
        # the demand facility.
        bid_block = body[bid_heading:demand_heading]
        self.assertNotIn("Grand Hotel", bid_block)


class MainDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.leads = self.tmp / "leads.csv"
        self.demand = self.tmp / "demand.csv"

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
                            "--demand", str(self.demand),
                            "--created-date", "2026-06-27", "--pr-url", "https://gh/pr/5",
                            "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)
        self.assertIn("Jail Mattresses", out)
        self.assertIn("https://gh/pr/5", out)

    def test_dry_run_includes_demand_section(self) -> None:
        pipeline.write_rows_atomic(self.active, [
            _active_row(opportunity_id="a", title="Jail Mattresses", source="Bonfire",
                        created_date="2026-06-27"),
        ])
        demand_radar.write_demand_rows_atomic(self.demand, [
            _demand_row(demand_id="d1", segment="hotel", scale="200 keys",
                        est_buy_window="2026-09", location="TX",
                        facility_name="Grand Hotel", source_url="https://news/h",
                        first_seen="2026-06-27"),
            _demand_row(demand_id="d-old", segment="hotel", facility_name="Old Tower",
                        first_seen="2026-01-01"),
        ])
        rc, out = self._run("--active", str(self.active), "--leads", str(self.leads),
                            "--demand", str(self.demand),
                            "--created-date", "2026-06-27", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("1 demand", out)
        self.assertIn("DEMAND RADAR", out)
        self.assertIn("Grand Hotel", out)
        self.assertNotIn("Old Tower", out)

    def test_no_new_rows_sends_nothing(self) -> None:
        pipeline.write_rows_atomic(self.active, [
            _active_row(opportunity_id="a", title="Old", created_date="2026-01-01"),
        ])
        rc, out = self._run("--active", str(self.active), "--leads", str(self.leads),
                            "--demand", str(self.demand),
                            "--created-date", "2026-06-27", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("nothing new", out)

    def test_failure_mode_dry_run(self) -> None:
        rc, out = self._run("--failure", "--run-url", "https://gh/run/9",
                            "--created-date", "2026-06-27", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("PIPELINE FAILED", out)
        self.assertIn("https://gh/run/9", out)

    def test_watchdog_mode_dry_run(self) -> None:
        rc, out = self._run("--watchdog", "--window", "7",
                            "--run-url", "https://gh/run/12", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("WATCHDOG", out)
        self.assertIn("7 runs with ZERO", out)
        self.assertIn("https://gh/run/12", out)


if __name__ == "__main__":
    unittest.main()
