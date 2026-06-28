"""Unit tests for tools/demand_radar.py. Stdlib unittest, no network."""

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

import demand_radar  # noqa: E402
import demand_signal  # noqa: E402


def _header_of(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


class _StubVerdict:
    """Minimal stand-in shaped like demand_signal.DemandVerdict."""

    def __init__(self, **over):
        self.segment = over.get("segment", "hotel")
        self.scale_value = over.get("scale_value", 180)
        self.scale_unit = over.get("scale_unit", "keys")
        self.project_stage = over.get("project_stage", "under-construction")
        self.est_buy_window = over.get("est_buy_window", "2027-09")
        self.est_completion_date = over.get("est_completion_date", "2027")
        self.states = over.get("states", ["TX"])
        self.reasons = over.get("reasons", ["facility (hotel): marriott",
                                           "project trigger: breaks ground -> under-construction"])


class HeaderTests(unittest.TestCase):
    def test_committed_review_file_matches_canonical_header(self) -> None:
        self.assertEqual(_header_of(demand_radar.DEFAULT_REVIEW), demand_radar.DEMAND_HEADER)

    def test_committed_archive_file_matches_canonical_header(self) -> None:
        self.assertEqual(_header_of(demand_radar.DEFAULT_ARCHIVE), demand_radar.DEMAND_HEADER)

    def test_template_matches_canonical_header(self) -> None:
        self.assertEqual(_header_of(demand_radar.TEMPLATE_HEADER), demand_radar.DEMAND_HEADER)

    def test_all_three_headers_identical(self) -> None:
        review = _header_of(demand_radar.DEFAULT_REVIEW)
        self.assertEqual(review, _header_of(demand_radar.DEFAULT_ARCHIVE))
        self.assertEqual(review, _header_of(demand_radar.TEMPLATE_HEADER))


class BuildDemandRowTests(unittest.TestCase):
    def test_maps_verdict_fields(self) -> None:
        v = _StubVerdict()
        row = demand_radar.build_demand_row(
            "Marriott Courtyard Dallas", "ConstructionWire", v, "2026-06-28",
            source_url="https://example.com/x",
        )
        self.assertEqual(set(row), set(demand_radar.DEMAND_HEADER))
        self.assertEqual(row["status"], "reviewing")
        self.assertEqual(row["segment"], "hotel")
        self.assertEqual(row["scale"], "180 keys")
        self.assertEqual(row["project_stage"], "under-construction")
        self.assertEqual(row["est_buy_window"], "2027-09")
        self.assertEqual(row["est_completion_date"], "2027")
        self.assertEqual(row["location"], "TX")
        self.assertEqual(row["facility_name"], "Marriott Courtyard Dallas")
        self.assertEqual(row["signal_source"], "ConstructionWire")
        self.assertEqual(row["source_url"], "https://example.com/x")
        self.assertEqual(row["first_seen"], "2026-06-28")
        self.assertEqual(row["last_reviewed"], "2026-06-28")
        self.assertIn("2027-09", row["next_action"])  # WATCH near the buy-window
        self.assertTrue(row["notes"])
        self.assertEqual(
            row["demand_id"],
            demand_radar.demand_id_for("ConstructionWire", "hotel",
                                       "Marriott Courtyard Dallas", "TX"),
        )

    def test_no_buy_window_uses_review_next_action(self) -> None:
        v = _StubVerdict(est_buy_window="", scale_value=None, scale_unit="")
        row = demand_radar.build_demand_row("Some Hotel", "Src", v, "2026-06-28")
        self.assertEqual(row["scale"], "")
        self.assertEqual(row["est_buy_window"], "")
        self.assertTrue(row["next_action"].startswith("REVIEW:"))

    def test_real_demand_verdict_roundtrips(self) -> None:
        # Exercise the actual classifier so the mapping stays in sync with the
        # real DemandVerdict shape.
        verdict = demand_signal.classify_demand(
            "Marriott hotel breaks ground in Dallas, Texas; 180 keys, opening Q3 2027")
        row = demand_radar.build_demand_row("Marriott Dallas", "ConstructionWire",
                                            verdict, "2026-06-28")
        self.assertEqual(row["status"], "reviewing")
        self.assertEqual(row["segment"], "hotel")
        self.assertEqual(row["est_buy_window"], verdict.est_buy_window)
        self.assertTrue(row["demand_id"])


class MatchKeyTests(unittest.TestCase):
    def test_same_facility_location_dedups_across_review_and_archive(self) -> None:
        review_row = {"signal_source": "ConstructionWire", "segment": "hotel",
                      "facility_name": "Marriott Courtyard Dallas", "location": "TX",
                      "demand_id": "constructionwire-hotel-marriott-courtyard-dallas-tx"}
        archive_row = {"signal_source": "RealEstateDaily", "segment": "hotel",
                       "facility_name": "Marriott Courtyard Dallas", "location": "TX",
                       "demand_id": "realestatedaily-hotel-marriott-courtyard-dallas-tx"}
        self.assertTrue(
            demand_radar.demand_match_keys(review_row)
            & demand_radar.demand_match_keys(archive_row)
        )

    def test_different_facility_does_not_dedup(self) -> None:
        a = {"signal_source": "S", "segment": "hotel", "facility_name": "Hotel A",
             "location": "TX", "demand_id": "s-hotel-hotel-a-tx"}
        b = {"signal_source": "S", "segment": "hotel", "facility_name": "Hotel B",
             "location": "TX", "demand_id": "s-hotel-hotel-b-tx"}
        self.assertFalse(
            demand_radar.demand_match_keys(a) & demand_radar.demand_match_keys(b)
        )


class ReadWriteTests(unittest.TestCase):
    def test_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "demand.csv"
            v = _StubVerdict()
            row = demand_radar.build_demand_row("Marriott Dallas", "Src", v, "2026-06-28")
            demand_radar.write_demand_rows_atomic(path, [row])
            header, rows = demand_radar.read_demand_rows(path)
            self.assertEqual(header, demand_radar.DEMAND_HEADER)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["facility_name"], "Marriott Dallas")

    def test_header_drift_reordered_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "demand.csv"
            reordered = list(reversed(demand_radar.DEMAND_HEADER))
            with path.open("w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerow(reordered)
            with self.assertRaises(ValueError):
                demand_radar.read_demand_rows(path)

    def test_header_drift_short_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "demand.csv"
            with path.open("w", encoding="utf-8", newline="") as fh:
                csv.writer(fh, lineterminator="\n").writerow(demand_radar.DEMAND_HEADER[:5])
            with self.assertRaises(ValueError):
                demand_radar.read_demand_rows(path)


class _CliCase(unittest.TestCase):
    """Base class providing a temp review/archive workspace + run()."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        d = Path(self._tmp.name)
        self.review = d / "review.csv"
        self.archive = d / "archive.csv"
        self.pipeline = d / "_pipeline.csv"  # sentinel — Demand Radar must never write it
        demand_radar.write_demand_rows_atomic(self.review, [])
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, *argv: str) -> tuple[int, str]:
        out = io.StringIO()
        with redirect_stdout(out):
            rc = demand_radar.main(list(argv))
        return rc, out.getvalue()

    def _base(self) -> list[str]:
        return ["--review", str(self.review), "--archive", str(self.archive)]

    def add_signal(self, **over: str) -> tuple[int, str]:
        argv = self._base() + [
            "add",
            "--signal-source", over.get("signal_source", "ConstructionWire"),
            "--segment", over.get("segment", "hotel"),
            "--facility-name", over.get("facility_name", "Marriott Courtyard Dallas"),
        ]
        for flag in ("location", "scale", "project_stage", "est_buy_window",
                     "est_completion_date", "status", "demand_id"):
            if flag in over:
                argv += [f"--{flag.replace('_', '-')}", str(over[flag])]
        if over.get("overwrite"):
            argv.append("--overwrite")
        return self.run_cli(*argv)

    def review_rows(self) -> list[dict]:
        _, rows = demand_radar.read_demand_rows(self.review)
        return rows


class SummaryTests(_CliCase):
    def test_summary_on_empty_file(self) -> None:
        rc, out = self.run_cli(*self._base(), "summary")
        self.assertEqual(rc, 0)
        self.assertIn("Total signals: 0", out)
        self.assertIn("By segment:", out)
        self.assertIn("Buy-windows in next 180 days:", out)


class AddTests(_CliCase):
    def test_add_creates_valid_row(self) -> None:
        rc, _ = self.add_signal(location="TX", est_buy_window="2027-09",
                                project_stage="under-construction")
        self.assertEqual(rc, 0)
        rows = self.review_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["signal_source"], "ConstructionWire")
        self.assertEqual(row["segment"], "hotel")
        self.assertEqual(row["status"], "reviewing")
        self.assertEqual(row["est_buy_window"], "2027-09")
        self.assertTrue(row["demand_id"])

    def test_invalid_status_rejected(self) -> None:
        rc, _ = self.add_signal(status="bogus")
        self.assertEqual(rc, 1)

    def test_invalid_segment_rejected(self) -> None:
        rc, _ = self.run_cli(*self._base(), "add", "--signal-source", "S",
                             "--facility-name", "X", "--segment", "spaceport")
        self.assertEqual(rc, 1)

    def test_invalid_stage_rejected(self) -> None:
        rc, _ = self.add_signal(project_stage="not-a-stage")
        self.assertEqual(rc, 1)

    def test_invalid_buy_window_rejected(self) -> None:
        rc, _ = self.add_signal(est_buy_window="2027-13")
        self.assertEqual(rc, 1)

    def test_invalid_completion_date_rejected(self) -> None:
        rc, _ = self.add_signal(est_completion_date="not-a-date")
        self.assertEqual(rc, 1)

    def test_bare_year_completion_date_allowed(self) -> None:
        rc, _ = self.add_signal(est_completion_date="2027")
        self.assertEqual(rc, 0)

    def test_duplicate_demand_id_rejected_without_overwrite(self) -> None:
        rc, _ = self.add_signal()
        self.assertEqual(rc, 0)
        rc2, _ = self.add_signal()
        self.assertEqual(rc2, 1)
        self.assertEqual(len(self.review_rows()), 1)

    def test_duplicate_demand_id_allowed_with_overwrite(self) -> None:
        self.add_signal(est_buy_window="2027-09")
        rc, _ = self.add_signal(est_buy_window="2028-03", overwrite=True)
        self.assertEqual(rc, 0)
        rows = self.review_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["est_buy_window"], "2028-03")


class ArchiveTests(_CliCase):
    def test_archive_moves_row(self) -> None:
        self.add_signal()
        demand_id = self.review_rows()[0]["demand_id"]
        rc, _ = self.run_cli(*self._base(), "archive", demand_id, "--note", "project shelved")
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.review_rows()), 0)
        _, arch = demand_radar.read_demand_rows(self.archive)
        self.assertEqual(len(arch), 1)
        self.assertEqual(arch[0]["demand_id"], demand_id)
        self.assertEqual(arch[0]["status"], "archived")
        self.assertIn("project shelved", arch[0]["notes"])

    def test_archive_custom_status(self) -> None:
        self.add_signal()
        demand_id = self.review_rows()[0]["demand_id"]
        rc, _ = self.run_cli(*self._base(), "archive", demand_id, "--status", "no-fit")
        self.assertEqual(rc, 0)
        _, arch = demand_radar.read_demand_rows(self.archive)
        self.assertEqual(arch[0]["status"], "no-fit")

    def test_archive_missing_row_errors(self) -> None:
        rc, _ = self.run_cli(*self._base(), "archive", "does-not-exist")
        self.assertEqual(rc, 1)


class OutreachTests(_CliCase):
    def test_outreach_sets_status_and_notes(self) -> None:
        self.add_signal()
        demand_id = self.review_rows()[0]["demand_id"]
        rc, _ = self.run_cli(*self._base(), "outreach", demand_id,
                             "--contact", "Jane Dev (developer)",
                             "--note", "left voicemail")
        self.assertEqual(rc, 0)
        row = self.review_rows()[0]
        self.assertEqual(row["status"], "outreach")
        self.assertIn("Jane Dev", row["notes"])
        self.assertIn("left voicemail", row["notes"])
        self.assertTrue(row["next_action"].startswith("FOLLOW-UP"))

    def test_outreach_does_not_touch_pipeline(self) -> None:
        self.add_signal()
        demand_id = self.review_rows()[0]["demand_id"]
        self.assertFalse(self.pipeline.exists())
        rc, _ = self.run_cli(*self._base(), "outreach", demand_id,
                             "--contact", "GC firm")
        self.assertEqual(rc, 0)
        # Demand Radar is parallel to the bid pipeline: nothing under bids/ is
        # created or modified.
        self.assertFalse(self.pipeline.exists())

    def test_outreach_missing_row_errors(self) -> None:
        rc, _ = self.run_cli(*self._base(), "outreach", "nope", "--contact", "X")
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
