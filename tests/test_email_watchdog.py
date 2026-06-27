"""Unit tests for tools/email_watchdog.py. Stdlib unittest, no I/O."""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import email_watchdog  # noqa: E402


class ShouldAlertTests(unittest.TestCase):
    def test_all_zero_at_threshold_alerts(self) -> None:
        self.assertTrue(email_watchdog.should_alert([0, 0, 0, 0, 0, 0, 0], 7))

    def test_any_nonzero_does_not_alert(self) -> None:
        self.assertFalse(email_watchdog.should_alert([0, 0, 3, 0, 0, 0, 0], 7))

    def test_below_threshold_does_not_alert(self) -> None:
        # New system / not enough history -> never alarm.
        self.assertFalse(email_watchdog.should_alert([0, 0, 0], 7))

    def test_empty_does_not_alert(self) -> None:
        self.assertFalse(email_watchdog.should_alert([], 7))

    def test_more_than_threshold_all_zero_alerts(self) -> None:
        self.assertTrue(email_watchdog.should_alert([0] * 10, 7))


class CliTests(unittest.TestCase):
    def _run(self, *argv: str) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            email_watchdog.main(list(argv))
        return out.getvalue()

    def test_cli_emits_alert_true(self) -> None:
        out = self._run("--counts", "0 0 0 0 0 0 0", "--threshold", "7")
        self.assertIn("alert=true", out)

    def test_cli_emits_alert_false_on_activity(self) -> None:
        out = self._run("--counts", "0 1 0 0 0 0 0", "--threshold", "7")
        self.assertIn("alert=false", out)

    def test_cli_handles_empty_counts(self) -> None:
        out = self._run("--counts", "", "--threshold", "7")
        self.assertIn("alert=false", out)


if __name__ == "__main__":
    unittest.main()
