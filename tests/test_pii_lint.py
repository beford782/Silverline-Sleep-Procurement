"""Unit tests for tools/pii_lint.py. Stdlib unittest, no network/git."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import pii_lint  # noqa: E402


class ScanTextTests(unittest.TestCase):
    def _kinds(self, text: str, allow=None):
        return {kind for _ln, kind, _tok in pii_lint.scan_text(text, allow or set())}

    def test_detects_phone(self) -> None:
        self.assertIn("phone", self._kinds("call 512-555-1234 today"))
        self.assertIn("phone", self._kinds("fax 512.555.1234"))

    def test_detects_ein(self) -> None:
        self.assertIn("ein", self._kinds("EIN 12-3456789 on file"))

    def test_detects_street_address(self) -> None:
        self.assertIn("street-address", self._kinds("ship to 123 Maple Street"))
        self.assertIn("street-address", self._kinds("12 North Main Ave, suite 4"))

    def test_public_uei_is_not_flagged(self) -> None:
        self.assertEqual(
            pii_lint.scan_text("UEI XF73FG8CVMX1 is public", pii_lint.PUBLIC_ALLOWLIST),
            [])

    def test_allowlisted_literal_is_skipped(self) -> None:
        self.assertEqual(pii_lint.scan_text("call 512-555-1234", {"512-555-1234"}), [])

    def test_clean_text_has_no_hits(self) -> None:
        self.assertEqual(pii_lint.scan_text("Twin XL mattresses for the dorm", set()), [])

    def test_iso_date_not_mistaken_for_ein(self) -> None:
        # 2026-06-15 must not match the EIN pattern (\d{2}-\d{7}).
        self.assertEqual(self._kinds("posted 2026-06-15"), set())


class MainTests(unittest.TestCase):
    def test_whole_file_flags_pii(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "data.csv"
            f.write_text("id,phone\n1,210-555-9999\n", encoding="utf-8")
            self.assertEqual(pii_lint.main([str(f)]), 1)

    def test_whole_file_clean_passes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "data.csv"
            f.write_text("id,title\n1,Mattresses and box springs\n", encoding="utf-8")
            self.assertEqual(pii_lint.main([str(f)]), 0)

    def test_allow_flag_suppresses_match(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "data.csv"
            f.write_text("id,phone\n1,210-555-9999\n", encoding="utf-8")
            self.assertEqual(pii_lint.main([str(f), "--allow", "210-555-9999"]), 0)


if __name__ == "__main__":
    unittest.main()
