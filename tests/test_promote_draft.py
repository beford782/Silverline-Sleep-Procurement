"""Unit tests for tools/promote_draft.py. Stdlib unittest, tempfile-backed."""

from __future__ import annotations

import csv
import io
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

import pipeline  # noqa: E402
import promote_draft  # noqa: E402


def _write_pipeline(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            full = {k: "" for k in pipeline.CANONICAL_HEADER}
            full.update(row)
            writer.writerow(full)


def _row(opportunity_id: str, status: str = "watching") -> dict:
    return {
        "opportunity_id": opportunity_id,
        "status": status,
        "source": "Test Portal",
        "buyer": "Test Buyer",
        "solicitation_number": opportunity_id.upper(),
        "title": f"Title {opportunity_id}",
    }


class PromoteDraftTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active_csv = self.tmp / "bids" / "active" / "_pipeline.csv"
        self.archive_csv = self.tmp / "bids" / "archive" / "_pipeline_archive.csv"
        self.active_dir = self.tmp / "bids" / "active"
        self.archive_dir = self.tmp / "bids" / "archive"
        self.draft_dir = self.tmp / "build" / "drafts"
        self.draft_dir.mkdir(parents=True)
        _write_pipeline(self.active_csv, [_row("active-one")])
        _write_pipeline(self.archive_csv, [])
        (self.draft_dir / "active-one_draft.md").write_text("# Active One\n", encoding="utf-8")

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = promote_draft.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def _base(self, opportunity_id: str = "active-one") -> list[str]:
        return [
            opportunity_id,
            "--active", str(self.active_csv),
            "--archive", str(self.archive_csv),
            "--draft-dir", str(self.draft_dir),
            "--active-dir", str(self.active_dir),
            "--archive-dir", str(self.archive_dir),
        ]

    def test_happy_path_promotes_to_active_markdown(self) -> None:
        rc, out, err = self._run(*self._base())
        self.assertEqual(rc, 0, err)
        dest = self.active_dir / "active-one.md"
        self.assertTrue(dest.exists())
        self.assertEqual(dest.read_text(encoding="utf-8"), "# Active One\n")
        self.assertIn("promoted:", out)

    def test_missing_draft_errors_without_write(self) -> None:
        rc, _, err = self._run(*self._base("missing-one"))
        self.assertEqual(rc, 1)
        self.assertIn("active pipeline", err)
        self.assertFalse((self.active_dir / "missing-one.md").exists())

    def test_active_row_without_draft_errors(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one"), _row("active-two")])
        rc, _, err = self._run(*self._base("active-two"))
        self.assertEqual(rc, 1)
        self.assertIn("draft not found", err)
        self.assertFalse((self.active_dir / "active-two.md").exists())

    def test_archived_opportunity_errors(self) -> None:
        _write_pipeline(self.archive_csv, [_row("active-one", "no-bid")])
        rc, _, err = self._run(*self._base())
        self.assertEqual(rc, 1)
        self.assertIn("archive pipeline", err)

    def test_existing_destination_requires_force(self) -> None:
        dest = self.active_dir / "active-one.md"
        dest.write_text("# Existing\n", encoding="utf-8")
        rc, _, err = self._run(*self._base())
        self.assertEqual(rc, 1)
        self.assertIn("already exists", err)
        self.assertEqual(dest.read_text(encoding="utf-8"), "# Existing\n")

        rc2, _, err2 = self._run(*self._base(), "--force")
        self.assertEqual(rc2, 0, err2)
        self.assertEqual(dest.read_text(encoding="utf-8"), "# Active One\n")

    def test_archive_markdown_collision_requires_force(self) -> None:
        (self.archive_dir / "active-one.md").write_text("# Archived\n", encoding="utf-8")
        rc, _, err = self._run(*self._base())
        self.assertEqual(rc, 1)
        self.assertIn("already exists in archive", err)
        self.assertFalse((self.active_dir / "active-one.md").exists())

    def test_explicit_draft_and_output_paths(self) -> None:
        custom_draft = self.tmp / "custom.md"
        custom_out = self.tmp / "out.md"
        custom_draft.write_text("# Custom\n", encoding="utf-8")
        rc, _, err = self._run(
            *self._base(),
            "--draft", str(custom_draft),
            "--output", str(custom_out),
        )
        self.assertEqual(rc, 0, err)
        self.assertEqual(custom_out.read_text(encoding="utf-8"), "# Custom\n")

    def test_closed_active_status_errors(self) -> None:
        _write_pipeline(self.active_csv, [_row("active-one", "awarded")])
        rc, _, err = self._run(*self._base())
        self.assertEqual(rc, 1)
        self.assertIn("non-active status", err)


if __name__ == "__main__":
    unittest.main()
