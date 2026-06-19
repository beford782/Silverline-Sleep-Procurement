"""Unit tests for tools/lead_radar.py. Stdlib unittest, no network."""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import lead_radar  # noqa: E402
import pipeline  # noqa: E402


def _header_of(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


class HeaderTests(unittest.TestCase):
    def test_committed_review_file_matches_canonical_header(self) -> None:
        self.assertEqual(_header_of(lead_radar.DEFAULT_REVIEW), lead_radar.LEAD_HEADER)

    def test_template_matches_canonical_header(self) -> None:
        self.assertEqual(_header_of(lead_radar.TEMPLATE_HEADER), lead_radar.LEAD_HEADER)

    def test_review_and_template_headers_identical(self) -> None:
        self.assertEqual(
            _header_of(lead_radar.DEFAULT_REVIEW),
            _header_of(lead_radar.TEMPLATE_HEADER),
        )


class _CliCase(unittest.TestCase):
    """Base class providing a temp review/archive/active workspace + run()."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        self.review = d / "review.csv"
        self.archive = d / "archive.csv"
        self.active = d / "active.csv"
        lead_radar.write_lead_rows_atomic(self.review, [])
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = lead_radar.main(list(argv))
        return rc, out.getvalue()

    def _base(self) -> list[str]:
        return ["--review", str(self.review), "--archive", str(self.archive)]

    def add_lead(self, **over: str) -> tuple[int, str]:
        argv = self._base() + [
            "add",
            "--source", over.get("source", "IonWave"),
            "--buyer", over.get("buyer", "Region 6 ESC"),
            "--title", over.get("title", "School Furniture & Related Services"),
            "--lead-type", over.get("lead_type", "broad_furniture_ffe"),
        ]
        for flag in ("solicitation_number", "due_date", "trigger_terms", "status", "fit_score"):
            if flag in over:
                argv += [f"--{flag.replace('_', '-')}", str(over[flag])]
        if over.get("overwrite"):
            argv.append("--overwrite")
        return self.run_cli(*argv)

    def review_rows(self) -> list[dict]:
        _, rows = lead_radar.read_lead_rows(self.review)
        return rows


class SummaryTests(_CliCase):
    def test_summary_on_empty_file(self) -> None:
        rc, out = self.run_cli(*self._base(), "summary")
        self.assertEqual(rc, 0)
        self.assertIn("Total leads: 0", out)
        self.assertIn("By lead_type:", out)


class AddTests(_CliCase):
    def test_add_creates_valid_lead(self) -> None:
        rc, out = self.add_lead(solicitation_number="RFP 16.26", due_date="2026-07-15")
        self.assertEqual(rc, 0)
        rows = self.review_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["source"], "IonWave")
        self.assertEqual(row["solicitation_number"], "RFP 16.26")
        self.assertEqual(row["status"], "watching")
        self.assertEqual(row["lead_type"], "broad_furniture_ffe")
        self.assertTrue(row["lead_id"])
        self.assertTrue(set(row).issuperset(set(lead_radar.LEAD_HEADER)))

    def test_invalid_status_rejected(self) -> None:
        rc, _ = self.run_cli(*self._base(), "add", "--source", "X", "--buyer", "Y",
                             "--title", "Z", "--status", "bogus")
        self.assertEqual(rc, 1)

    def test_invalid_lead_type_rejected(self) -> None:
        rc, _ = self.run_cli(*self._base(), "add", "--source", "X", "--buyer", "Y",
                             "--title", "Z", "--lead-type", "not-a-type")
        self.assertEqual(rc, 1)

    def test_duplicate_lead_id_rejected_without_overwrite(self) -> None:
        rc, _ = self.add_lead(solicitation_number="RFP 16.26")
        self.assertEqual(rc, 0)
        rc2, _ = self.add_lead(solicitation_number="RFP 16.26")
        self.assertEqual(rc2, 1)
        self.assertEqual(len(self.review_rows()), 1)

    def test_duplicate_lead_id_allowed_with_overwrite(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26", due_date="2026-07-15")
        rc, _ = self.add_lead(solicitation_number="RFP 16.26", due_date="2026-08-01", overwrite=True)
        self.assertEqual(rc, 0)
        rows = self.review_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["due_date"], "2026-08-01")


class ArchiveTests(_CliCase):
    def test_archive_moves_row(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26")
        lead_id = self.review_rows()[0]["lead_id"]

        rc, out = self.run_cli(*self._base(), "archive", lead_id, "--note", "expired furniture")
        self.assertEqual(rc, 0)
        # Removed from review ...
        self.assertEqual(len(self.review_rows()), 0)
        # ... and present in archive with terminal status + appended note.
        _, arch = lead_radar.read_lead_rows(self.archive)
        self.assertEqual(len(arch), 1)
        self.assertEqual(arch[0]["lead_id"], lead_id)
        self.assertEqual(arch[0]["status"], "archived")
        self.assertIn("expired furniture", arch[0]["notes"])

    def test_archive_custom_status(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26")
        lead_id = self.review_rows()[0]["lead_id"]
        rc, _ = self.run_cli(*self._base(), "archive", lead_id, "--status", "no-fit")
        self.assertEqual(rc, 0)
        _, arch = lead_radar.read_lead_rows(self.archive)
        self.assertEqual(arch[0]["status"], "no-fit")

    def test_archive_missing_lead_errors(self) -> None:
        rc, _ = self.run_cli(*self._base(), "archive", "does-not-exist")
        self.assertEqual(rc, 1)


class PromoteTests(_CliCase):
    def test_promote_requires_confirmed_products(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26")
        lead_id = self.review_rows()[0]["lead_id"]
        # argparse marks --confirmed-products required -> SystemExit(2).
        with self.assertRaises(SystemExit):
            self.run_cli(*self._base(), "promote", lead_id, "--active", str(self.active))

    def test_promote_writes_active_and_marks_lead(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26", trigger_terms="furniture; ff&e", fit_score="35")
        lead_id = self.review_rows()[0]["lead_id"]

        rc, out = self.run_cli(
            *self._base(), "promote", lead_id,
            "--confirmed-products", "mattresses; bed frames",
            "--active", str(self.active),
        )
        self.assertEqual(rc, 0)

        # Active pipeline got exactly one row, status watching, products confirmed.
        _, active_rows = pipeline.read_rows(self.active)
        self.assertEqual(len(active_rows), 1)
        arow = active_rows[0]
        self.assertEqual(arow["status"], "watching")
        self.assertEqual(arow["primary_products"], "mattresses; bed frames")
        self.assertEqual(arow["commodity_terms"], "furniture; ff&e")
        self.assertIn("Promoted from Lead Radar", arow["notes"])

        # Lead is kept and marked promoted.
        rows = self.review_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "promoted")
        self.assertIn(arow["opportunity_id"], rows[0]["notes"])

    def test_promote_dedupes_against_active(self) -> None:
        self.add_lead(solicitation_number="RFP 16.26")
        lead_id = self.review_rows()[0]["lead_id"]
        for _ in range(2):
            rc, _out = self.run_cli(
                *self._base(), "promote", lead_id,
                "--confirmed-products", "mattresses",
                "--active", str(self.active),
            )
            self.assertEqual(rc, 0)
        _, active_rows = pipeline.read_rows(self.active)
        self.assertEqual(len(active_rows), 1)  # not duplicated


if __name__ == "__main__":
    unittest.main()
