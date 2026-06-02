"""Unit tests for tools/portal_csv_mapping.py."""

from __future__ import annotations

import io
import json
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

import portal_csv_mapping  # noqa: E402


class PortalCsvMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def _csv(self, header_line: str, body: str = "x\n") -> Path:
        path = self.tmp / "export.csv"
        path.write_text(header_line + "\n" + body, encoding="utf-8")
        return path

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = portal_csv_mapping.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def test_suggest_columns_from_common_headers(self) -> None:
        headers = [
            "Bid #",
            "Event Title",
            "Issuing Agency",
            "Posting URL",
            "Open Date",
            "Close Date",
            "Questions Due",
            "NIGP Code",
            "Budget",
            "Notice Type",
        ]
        suggestions = portal_csv_mapping.suggest_columns(headers)
        self.assertEqual(suggestions["solicitation_number"], "Bid #")
        self.assertEqual(suggestions["title"], "Event Title")
        self.assertEqual(suggestions["buyer"], "Issuing Agency")
        self.assertEqual(suggestions["portal_url"], "Posting URL")
        self.assertEqual(suggestions["posted_date"], "Open Date")
        self.assertEqual(suggestions["due_date"], "Close Date")
        self.assertEqual(suggestions["question_deadline"], "Questions Due")
        self.assertEqual(suggestions["commodity_terms"], "NIGP Code")
        self.assertEqual(suggestions["estimated_value"], "Budget")
        self.assertEqual(suggestions["notes"], "Notice Type")

    def test_render_report_lists_unmapped_headers(self) -> None:
        headers = ["Solicitation #", "Title", "Mystery Column"]
        mapping = portal_csv_mapping.build_mapping("Fake Portal", headers, ["%Y-%m-%d"])
        report = portal_csv_mapping.render_report(headers, mapping)
        self.assertIn("solicitation_number: Solicitation #", report)
        self.assertIn("- Mystery Column", report)

    def test_cli_preview_does_not_write(self) -> None:
        csv_path = self._csv("Solicitation #,Title,Agency\nA,Title,Buyer\n")
        output = self.tmp / "mapping.json"
        rc, out, err = self._run(
            str(csv_path),
            "--source", "Fake Portal",
            "--output", str(output),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("Suggested mapping", out)
        self.assertIn("preview only", out)
        self.assertFalse(output.exists())

    def test_cli_write_outputs_valid_mapping(self) -> None:
        csv_path = self._csv("Solicitation #,Title,Agency,Due Date\nA,Title,Buyer,2026-06-01\n")
        output = self.tmp / "mapping.json"
        rc, out, err = self._run(
            str(csv_path),
            "--source", "Fake Portal",
            "--output", str(output),
            "--write",
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("wrote:", out)
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["source"], "Fake Portal")
        self.assertEqual(data["columns"]["due_date"], "Due Date")
        self.assertEqual(data["date_formats"], ["%m/%d/%Y", "%Y-%m-%d"])

    def test_cli_refuses_overwrite_without_force(self) -> None:
        csv_path = self._csv("Title\nT\n")
        output = self.tmp / "mapping.json"
        output.write_text("{}", encoding="utf-8")
        rc, _, err = self._run(
            str(csv_path),
            "--source", "Fake Portal",
            "--output", str(output),
            "--write",
        )
        self.assertEqual(rc, 1)
        self.assertIn("already exists", err)

    def test_cli_force_overwrites(self) -> None:
        csv_path = self._csv("Title\nT\n")
        output = self.tmp / "mapping.json"
        output.write_text("{}", encoding="utf-8")
        rc, _, err = self._run(
            str(csv_path),
            "--source", "Fake Portal",
            "--output", str(output),
            "--write",
            "--force",
        )
        self.assertEqual(rc, 0, err)
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["columns"]["title"], "Title")

    def test_cli_custom_date_formats(self) -> None:
        csv_path = self._csv("Due Date\n06/01/2026\n")
        output = self.tmp / "mapping.json"
        rc, _, err = self._run(
            str(csv_path),
            "--source", "Fake Portal",
            "--output", str(output),
            "--date-formats", "%d/%m/%Y,%Y-%m-%d",
            "--write",
        )
        self.assertEqual(rc, 0, err)
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["date_formats"], ["%d/%m/%Y", "%Y-%m-%d"])

    def test_missing_csv_path_errors(self) -> None:
        rc, _, err = self._run(str(self.tmp / "missing.csv"), "--source", "Fake Portal")
        self.assertEqual(rc, 2)
        self.assertIn("csv_path not found", err)


if __name__ == "__main__":
    unittest.main()
