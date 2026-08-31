"""Unit tests for tools/pipeline.py `deadlines` + `calendar` (send-by).

Stdlib unittest, tempfile-backed. These cover the gap that let two active rows
sit 12 days past their 2026-08-19 deadlines while the digest said "0 missed":
the deadline scan only read Lead Radar.
"""

from __future__ import annotations

import io
import json
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pipeline  # noqa: E402

TODAY = date(2026, 8, 31)


def row(**kw) -> dict:
    base = {k: "" for k in pipeline.CANONICAL_HEADER}
    base.update(kw)
    return base


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pipeline.write_rows_atomic(path, rows)


class DeadlineTriageTests(unittest.TestCase):
    def test_open_row_past_due_is_a_miss(self) -> None:
        crtc = row(opportunity_id="crtc", status="drafting", gate_status="bid_ready",
                   due_date="2026-08-19", created_date="2026-08-13")
        rep = pipeline.triage_deadlines([crtc], TODAY, 10)
        self.assertEqual([r["opportunity_id"] for _, r in rep["missed"]], ["crtc"])
        self.assertEqual(rep["missed"][0][0], -12)
        self.assertEqual(rep["due_soon"], [])

    def test_submitted_past_due_is_awaiting_award_not_a_miss(self) -> None:
        sub = row(opportunity_id="crtc", status="submitted", gate_status="bid_ready",
                  due_date="2026-08-19", created_date="2026-08-13")
        rep = pipeline.triage_deadlines([sub], TODAY, 10)
        self.assertEqual(rep["missed"], [])
        self.assertEqual([(d, r["opportunity_id"]) for d, r in rep["awaiting_award"]], [(12, "crtc")])

    def test_due_soon_inside_window_and_not_outside(self) -> None:
        soon = row(opportunity_id="soon", status="watching", due_date="2026-09-08", created_date="2026-08-27")
        later = row(opportunity_id="later", status="watching", due_date="2026-09-30", created_date="2026-08-27")
        rep = pipeline.triage_deadlines([soon, later], TODAY, 10)
        self.assertEqual([(d, r["opportunity_id"]) for d, r in rep["due_soon"]], [(8, "soon")])

    def test_row_ingested_after_its_deadline_is_not_a_miss(self) -> None:
        hist = row(opportunity_id="hist", status="watching", due_date="2026-05-21", created_date="2026-06-21")
        rep = pipeline.triage_deadlines([hist], TODAY, 10)
        self.assertEqual(rep["missed"], [])
        self.assertEqual([r["opportunity_id"] for _, r in rep["arrived_closed"]], ["hist"])

    def test_blank_created_date_cannot_hide_a_miss(self) -> None:
        r = row(opportunity_id="x", status="watching", due_date="2026-08-19")
        rep = pipeline.triage_deadlines([r], TODAY, 10)
        self.assertEqual([r["opportunity_id"] for _, r in rep["missed"]], ["x"])

    def test_undated_open_rows_listed_and_terminal_rows_ignored(self) -> None:
        jbsa = row(opportunity_id="jbsa", status="watching")
        nobid = row(opportunity_id="dead", status="no-bid", due_date="2026-08-01", created_date="2026-07-01")
        won = row(opportunity_id="won", status="awarded", due_date="2026-04-23", created_date="2026-03-23")
        rep = pipeline.triage_deadlines([jbsa, nobid, won], TODAY, 10)
        self.assertEqual([r["opportunity_id"] for r in rep["undated"]], ["jbsa"])
        self.assertEqual(rep["missed"], [])
        self.assertEqual(rep["awaiting_award"], [])

    def test_cmd_prints_missed_block_and_counts(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            active = tmp / "_pipeline.csv"
            _write_csv(active, [
                row(opportunity_id="crtc", status="drafting", gate_status="bid_ready",
                    solicitation_number="W50S7K26A005", title="CRTC Replacement Mattresses",
                    due_date="2026-08-19", created_date="2026-08-13"),
                row(opportunity_id="va", status="submitted", solicitation_number="36C25526Q0607",
                    title="Mattress for Behavior Health", due_date="2026-08-19", created_date="2026-08-13"),
            ])
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pipeline.main(["--active", str(active), "deadlines", "--today", "2026-08-31"])
            out = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("1 missed, 0 due soon, 0 open with no due date, 1 submitted awaiting award", out)
            self.assertIn("MISSED - active row held past its response deadline (1):", out)
            self.assertIn("W50S7K26A005", out)
            self.assertIn("SUBMITTED - awaiting award (1):", out)
            self.assertIn("12d since due 2026-08-19", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class SendByCalendarTests(unittest.TestCase):
    def test_bid_ready_row_gets_event_two_days_before_due(self) -> None:
        r = row(opportunity_id="bia", status="watching", gate_status="bid_ready",
                solicitation_number="140A2326Q0283", title="Residential Housing Mattresses",
                due_date="2026-09-08", buyer="BIE")
        payload = pipeline.build_send_by_payload([r], TODAY, 45)
        self.assertEqual(len(payload["events"]), 1)
        ev = payload["events"][0]
        self.assertEqual(ev["key"], "bia:2026-09-08")
        self.assertEqual(ev["start"], "2026-09-06")
        self.assertTrue(ev["all_day"])
        self.assertFalse(ev["overdue"])
        self.assertFalse(ev["past_due"])
        self.assertFalse(ev["already_scheduled"])
        self.assertIn("[SEND BY] 140A2326Q0283 Residential Housing Mattresses - due 2026-09-08", ev["title"])
        self.assertIn("Send checklist:", ev["description"])
        self.assertIn("silverlinesleep.com", ev["description"])
        self.assertEqual(payload["warnings"], [])

    def test_send_by_already_passed_is_flagged_overdue_not_dropped(self) -> None:
        r = row(opportunity_id="x", status="drafting", gate_status="bid_ready", due_date="2026-09-01")
        ev = pipeline.build_send_by_payload([r], TODAY, 45)["events"][0]
        self.assertEqual(ev["start"], "2026-08-30")
        self.assertTrue(ev["overdue"])
        self.assertFalse(ev["past_due"])

    def test_drafting_row_is_candidate_even_if_gate_blocked(self) -> None:
        r = row(opportunity_id="d", status="drafting", gate_status="blocked",
                compliance_blocker="specs_pending", due_date="2026-09-10")
        payload = pipeline.build_send_by_payload([r], TODAY, 45)
        self.assertEqual([e["opportunity_id"] for e in payload["events"]], ["d"])

    def test_blocked_watching_row_due_in_horizon_warns(self) -> None:
        r = row(opportunity_id="bia", status="watching", gate_status="blocked",
                compliance_blocker="set_aside_ineligible:ISBEE; specs_pending", due_date="2026-09-08")
        payload = pipeline.build_send_by_payload([r], TODAY, 45)
        self.assertEqual(payload["events"], [])
        self.assertEqual(len(payload["warnings"]), 1)
        self.assertIn("due in 8d but gate is blocked (set_aside_ineligible:ISBEE; specs_pending)",
                      payload["warnings"][0]["message"])

    def test_submitted_terminal_and_beyond_horizon_rows_excluded(self) -> None:
        sub = row(opportunity_id="s", status="submitted", gate_status="bid_ready", due_date="2026-09-05")
        dead = row(opportunity_id="n", status="no-bid", gate_status="bid_ready", due_date="2026-09-05")
        far = row(opportunity_id="f", status="watching", gate_status="bid_ready", due_date="2026-12-01")
        payload = pipeline.build_send_by_payload([sub, dead, far], TODAY, 45)
        self.assertEqual(payload["events"], [])
        self.assertEqual(payload["warnings"], [])

    def test_candidate_without_due_date_warns(self) -> None:
        r = row(opportunity_id="jbsa", status="watching", gate_status="bid_ready")
        payload = pipeline.build_send_by_payload([r], TODAY, 45)
        self.assertEqual(payload["events"], [])
        self.assertIn("no due_date", payload["warnings"][0]["message"])

    def test_already_scheduled_read_from_state(self) -> None:
        r = row(opportunity_id="x", status="drafting", gate_status="bid_ready", due_date="2026-09-20")
        state = {"x:2026-09-20": {"event_id": "abc", "created": "2026-08-31"}}
        ev = pipeline.build_send_by_payload([r], TODAY, 45, state)["events"][0]
        self.assertTrue(ev["already_scheduled"])

    def test_cmd_writes_payload_and_stdout_prints_json_only_with_events(self) -> None:
        tmp = Path(tempfile.mkdtemp())
        try:
            active = tmp / "_pipeline.csv"
            _write_csv(active, [
                row(opportunity_id="x", status="drafting", gate_status="bid_ready",
                    solicitation_number="SOL-1", title="Twin XL mattresses", due_date="2026-09-20"),
            ])
            out = tmp / "events.json"
            state = tmp / "state.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = pipeline.main(["--active", str(active), "calendar", "--today", "2026-08-31",
                                    "--out", str(out), "--state", str(state)])
            self.assertEqual(rc, 0)
            self.assertIn("Send-by reminders (as of 2026-08-31, horizon 45d): 1 event(s), 0 warning(s)", buf.getvalue())
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["events"][0]["start"], "2026-09-18")

            # --stdout with no events prints the table but no JSON blob.
            _write_csv(active, [row(opportunity_id="q", status="watching", gate_status="triage")])
            buf = io.StringIO()
            with redirect_stdout(buf):
                pipeline.main(["--active", str(active), "calendar", "--today", "2026-08-31",
                               "--stdout", "--state", str(state)])
            self.assertIn("(no bid_ready/drafting rows with a due date in horizon)", buf.getvalue())
            self.assertNotIn('"events"', buf.getvalue())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
