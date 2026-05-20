"""Unit tests for tools/ingest_portal_csv.py. Stdlib unittest, no network."""

from __future__ import annotations

import csv
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
ESBD_FIXTURE = ROOT / "tests" / "fixtures" / "esbd_export_sample.csv"
ESBD_CONFIG = ROOT / "configs" / "portal_csv" / "esbd.json"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ingest_portal_csv  # noqa: E402
import pipeline  # noqa: E402


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _seed_empty_pipeline(path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(",".join(pipeline.CANONICAL_HEADER) + "\n")


# ---------------------------------------------------------------------
# Mapping loader
# ---------------------------------------------------------------------

class MappingLoadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)

    def _write(self, payload) -> Path:
        p = self.tmp / "mapping.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return p

    def test_valid_mapping_loads(self) -> None:
        p = self._write({"source": "X", "columns": {"title": "T"}, "date_formats": ["%m/%d/%Y"]})
        data = ingest_portal_csv.load_mapping(p)
        self.assertEqual(data["source"], "X")
        self.assertEqual(data["columns"]["title"], "T")

    def test_unknown_top_level_key_errors(self) -> None:
        p = self._write({"source": "X", "colums": {}})  # typo intentional
        with self.assertRaises(ValueError) as ctx:
            ingest_portal_csv.load_mapping(p)
        self.assertIn("colums", str(ctx.exception))

    def test_unknown_canonical_field_errors(self) -> None:
        p = self._write({"source": "X", "columns": {"buyers": "B"}})
        with self.assertRaises(ValueError) as ctx:
            ingest_portal_csv.load_mapping(p)
        self.assertIn("buyers", str(ctx.exception))

    def test_columns_must_be_object(self) -> None:
        p = self._write({"source": "X", "columns": "not-an-object"})
        with self.assertRaises(ValueError):
            ingest_portal_csv.load_mapping(p)

    def test_date_formats_must_be_list_of_strings(self) -> None:
        p = self._write({"source": "X", "columns": {}, "date_formats": [1, 2, 3]})
        with self.assertRaises(ValueError):
            ingest_portal_csv.load_mapping(p)

    def test_committed_esbd_config_loads(self) -> None:
        # Smoke test: the committed config is structurally valid.
        data = ingest_portal_csv.load_mapping(ESBD_CONFIG)
        self.assertEqual(data["source"], "Texas ESBD")
        self.assertIn("solicitation_number", data["columns"])


# ---------------------------------------------------------------------
# Source / column precedence
# ---------------------------------------------------------------------

class ResolveTests(unittest.TestCase):
    def test_cli_source_overrides_mapping_source(self) -> None:
        self.assertEqual(
            ingest_portal_csv.resolve_source({"source": "From Mapping"}, "From CLI"),
            "From CLI",
        )

    def test_missing_source_raises(self) -> None:
        with self.assertRaises(ValueError):
            ingest_portal_csv.resolve_source({}, None)

    def test_cli_column_overrides_mapping_column(self) -> None:
        mapping = {"columns": {"buyer": "MappingBuyer", "title": "MappingTitle"}}
        out = ingest_portal_csv.resolve_columns(mapping, {"buyer": "CliBuyer"})
        self.assertEqual(out["buyer"], "CliBuyer")
        self.assertEqual(out["title"], "MappingTitle")

    def test_unmapped_fields_are_omitted(self) -> None:
        mapping = {"columns": {"title": "T"}}
        out = ingest_portal_csv.resolve_columns(mapping, {})
        self.assertEqual(out, {"title": "T"})


# ---------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------

class DateNormalizationTests(unittest.TestCase):
    def test_mmddyyyy_parsed(self) -> None:
        bad: list[str] = []
        self.assertEqual(
            ingest_portal_csv.normalize_date("05/01/2026", ["%m/%d/%Y"], bad),
            "2026-05-01",
        )
        self.assertEqual(bad, [])

    def test_iso_fallback(self) -> None:
        bad: list[str] = []
        self.assertEqual(
            ingest_portal_csv.normalize_date("2026-05-01", [], bad),
            "2026-05-01",
        )
        self.assertEqual(bad, [])

    def test_iso_with_timezone_parses(self) -> None:
        bad: list[str] = []
        self.assertEqual(
            ingest_portal_csv.normalize_date("2026-06-15T17:00:00-04:00", [], bad),
            "2026-06-15",
        )
        self.assertEqual(bad, [])

    def test_empty_is_empty(self) -> None:
        bad: list[str] = []
        self.assertEqual(ingest_portal_csv.normalize_date("", ["%m/%d/%Y"], bad), "")
        self.assertEqual(bad, [])

    def test_unparseable_records_failure(self) -> None:
        bad: list[str] = []
        result = ingest_portal_csv.normalize_date("not-a-date", ["%m/%d/%Y"], bad)
        self.assertEqual(result, "")
        self.assertEqual(bad, ["not-a-date"])


# ---------------------------------------------------------------------
# Estimated value
# ---------------------------------------------------------------------

class EstimatedValueTests(unittest.TestCase):
    def test_strips_dollar_and_comma(self) -> None:
        self.assertEqual(ingest_portal_csv.clean_estimated_value("$1,234.56"), "1234.56")

    def test_non_numeric_passes_through(self) -> None:
        self.assertEqual(ingest_portal_csv.clean_estimated_value("approx 5k"), "approx 5k")

    def test_empty_stays_empty(self) -> None:
        self.assertEqual(ingest_portal_csv.clean_estimated_value(""), "")


# ---------------------------------------------------------------------
# Row mapping + ingest unit
# ---------------------------------------------------------------------

class IngestUnitTests(unittest.TestCase):
    def _columns(self) -> dict[str, str]:
        return {
            "solicitation_number": "PLACEHOLDER_solicitation",
            "title": "PLACEHOLDER_title",
            "buyer": "PLACEHOLDER_agency",
            "portal_url": "PLACEHOLDER_url",
            "posted_date": "PLACEHOLDER_posted",
            "due_date": "PLACEHOLDER_due",
            "delivery_location": "PLACEHOLDER_location",
            "commodity_terms": "PLACEHOLDER_class",
            "notes": "PLACEHOLDER_notice_type",
        }

    def _csv_row(self, **overrides) -> dict:
        row = {
            "PLACEHOLDER_solicitation": "PLC-001",
            "PLACEHOLDER_title": "Synthetic A",
            "PLACEHOLDER_agency": "Alpha Agency",
            "PLACEHOLDER_url": "https://example.invalid/notice/PLC-001",
            "PLACEHOLDER_posted": "05/01/2026",
            "PLACEHOLDER_due": "06/15/2026",
            "PLACEHOLDER_location": "Austin, TX",
            "PLACEHOLDER_class": "NIGP 71500",
            "PLACEHOLDER_notice_type": "Solicitation",
        }
        row.update(overrides)
        return row

    def test_csv_row_to_pipeline_row_maps_fields(self) -> None:
        bad: list[str] = []
        row = ingest_portal_csv.csv_row_to_pipeline_row(
            self._csv_row(),
            self._columns(),
            source="Texas ESBD",
            date_formats=["%m/%d/%Y"],
            today="2026-05-20",
            bad_dates=bad,
        )
        self.assertEqual(row["source"], "Texas ESBD")
        self.assertEqual(row["solicitation_number"], "PLC-001")
        self.assertEqual(row["title"], "Synthetic A")
        self.assertEqual(row["buyer"], "Alpha Agency")
        self.assertEqual(row["due_date"], "2026-06-15")
        self.assertEqual(row["posted_date"], "2026-05-01")
        self.assertEqual(row["status"], "watching")
        self.assertEqual(row["created_date"], "2026-05-20")
        self.assertEqual(row["last_reviewed"], "2026-05-20")
        self.assertIn("Triage:", row["next_action"])
        self.assertEqual(row["notes"], "Solicitation")
        # opportunity_id comes from the shared helper - no inline duplication.
        expected_id = pipeline.derive_opportunity_id(
            "Texas ESBD", "Alpha Agency", "PLC-001", "Synthetic A"
        )
        self.assertEqual(row["opportunity_id"], expected_id)
        self.assertEqual(bad, [])

    def test_unparseable_date_leaves_field_empty_and_records_warning(self) -> None:
        bad: list[str] = []
        row = ingest_portal_csv.csv_row_to_pipeline_row(
            self._csv_row(PLACEHOLDER_due="not-a-date"),
            self._columns(),
            source="Texas ESBD",
            date_formats=["%m/%d/%Y"],
            today="2026-05-20",
            bad_dates=bad,
        )
        self.assertEqual(row["due_date"], "")
        # Posted date still parses cleanly; only due was bad.
        self.assertEqual(row["posted_date"], "2026-05-01")
        self.assertEqual(bad, ["not-a-date"])

    def test_intra_batch_dedup_counted_as_active(self) -> None:
        # Two identical CSV rows in one batch - only one row in new_rows,
        # the second counts as an active dupe.
        rows = [self._csv_row(), self._csv_row()]
        new, n_active, n_archive, bad = ingest_portal_csv.ingest(
            rows,
            self._columns(),
            "Texas ESBD",
            ["%m/%d/%Y"],
            existing_active=[],
            existing_archive=[],
            today="2026-05-20",
        )
        self.assertEqual(len(new), 1)
        self.assertEqual(n_active, 1)
        self.assertEqual(n_archive, 0)
        self.assertEqual(bad, [])

    def test_archive_match_wins_over_active_match_for_attribution(self) -> None:
        # Row appears in BOTH active and archive - must attribute to archive
        # ("previously closed, do not re-open" is the higher-priority signal).
        new_row = ingest_portal_csv.csv_row_to_pipeline_row(
            self._csv_row(),
            self._columns(),
            "Texas ESBD",
            ["%m/%d/%Y"],
            "2026-05-20",
            [],
        )
        new, n_active, n_archive, _ = ingest_portal_csv.ingest(
            [self._csv_row()],
            self._columns(),
            "Texas ESBD",
            ["%m/%d/%Y"],
            existing_active=[new_row],
            existing_archive=[new_row],
            today="2026-05-20",
        )
        self.assertEqual(new, [])
        self.assertEqual(n_active, 0)
        self.assertEqual(n_archive, 1)


# ---------------------------------------------------------------------
# CLI end-to-end (using committed fixture + config)
# ---------------------------------------------------------------------

class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.active = self.tmp / "active.csv"
        self.archive = self.tmp / "archive.csv"
        _seed_empty_pipeline(self.active)
        _seed_empty_pipeline(self.archive)

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = ingest_portal_csv.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def test_fixture_writes_three_rows_with_warning_for_bad_dates(self) -> None:
        rc, out, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("Texas ESBD fetched: 3", out)
        self.assertIn("new:    3", out)
        self.assertIn("dupes:  0 (0 active, 0 archive)", out)
        self.assertIn("wrote 3 new row(s)", out)

        # Warning on stderr for the row with both dates unparseable.
        self.assertIn("warning:", err)
        self.assertIn("unparseable date", err)
        # Two bad date *values* (posted + due) on one row.
        self.assertIn("2 unparseable", err)

        rows = _read_csv(self.active)
        row1 = next(r for r in rows if r["solicitation_number"] == "ESBD-2026-0001")
        row2 = next(r for r in rows if r["solicitation_number"] == "ESBD-2026-0002")
        row3 = next(r for r in rows if r["solicitation_number"] == "ESBD-2026-0003")
        # MM/DD/YYYY parsed
        self.assertEqual(row1["posted_date"], "2026-05-01")
        self.assertEqual(row1["due_date"], "2026-06-15")
        # ISO parsed via fromisoformat fallback (or the second strptime format)
        self.assertEqual(row2["posted_date"], "2026-05-08")
        self.assertEqual(row2["due_date"], "2026-06-22")
        # Unparseable -> empty
        self.assertEqual(row3["posted_date"], "")
        self.assertEqual(row3["due_date"], "")
        # Non-date fields on the bad-date row still come through.
        self.assertEqual(row3["title"], "Synthetic Mattress IFB C")
        self.assertEqual(row3["delivery_location"], "Dallas, TX")
        # All rows stamped with the config's source.
        self.assertTrue(all(r["source"] == "Texas ESBD" for r in rows))
        # All rows start in 'watching'.
        self.assertTrue(all(r["status"] == "watching" for r in rows))

    def test_dry_run_does_not_write(self) -> None:
        rc, out, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
            "--dry-run",
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("--dry-run", out)
        self.assertEqual(_read_csv(self.active), [])

    def test_second_run_dedupes_all_three_against_active(self) -> None:
        rc1, _, err1 = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc1, 0, err1)
        rc2, out2, err2 = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc2, 0, err2)
        self.assertIn("new:    0", out2)
        self.assertIn("dupes:  3 (3 active, 0 archive)", out2)
        self.assertIn("(no new rows to write)", out2)
        self.assertEqual(len(_read_csv(self.active)), 3)

    def test_archive_match_is_attributed_to_archive_not_active(self) -> None:
        # Pre-seed archive with ESBD-2026-0001 (matched via solicitation_number).
        with self.archive.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=pipeline.CANONICAL_HEADER, lineterminator="\n")
            w.writeheader()
            row = {k: "" for k in pipeline.CANONICAL_HEADER}
            row.update({
                "opportunity_id": "previously-closed-id",
                "source": "Texas ESBD",
                "buyer": "Whoever",
                "solicitation_number": "ESBD-2026-0001",
                "title": "previously closed",
                "status": "no-bid",
            })
            w.writerow(row)

        rc, out, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("new:    2", out)
        self.assertIn("dupes:  1 (0 active, 1 archive)", out)

        # Active gets only the 2 non-archived rows.
        active_rows = _read_csv(self.active)
        self.assertEqual(len(active_rows), 2)
        self.assertNotIn("ESBD-2026-0001", {r["solicitation_number"] for r in active_rows})

        # Archive untouched (still just the seed row).
        archive_rows = _read_csv(self.archive)
        self.assertEqual(len(archive_rows), 1)
        self.assertEqual(archive_rows[0]["opportunity_id"], "previously-closed-id")

    def test_cli_buyer_column_override_beats_mapping(self) -> None:
        # CSV uses a different header for buyer than the mapping config
        # (REAL_BUYER_HEADER instead of the mapping's "Agency").
        csv_path = self.tmp / "override.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            fh.write(
                "Solicitation #,Title,REAL_BUYER_HEADER,URL,Posted Date,"
                "Due Date,Delivery Location,Class/Item,Notice Type\n"
                "OV-1,Title,Override Agency,https://example.invalid/o,"
                "05/01/2026,06/01/2026,Austin,NIGP 71500,Solicitation\n"
            )
        rc, _, err = self._run(
            str(csv_path),
            "--mapping", str(ESBD_CONFIG),
            "--buyer-column", "REAL_BUYER_HEADER",
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        rows = _read_csv(self.active)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["buyer"], "Override Agency")

    def test_source_override_changes_stamp_and_summary(self) -> None:
        rc, out, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--source", "Texas Comptroller",
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("Texas Comptroller fetched: 3", out)
        rows = _read_csv(self.active)
        self.assertTrue(all(r["source"] == "Texas Comptroller" for r in rows))

    def test_missing_csv_header_errors(self) -> None:
        csv_path = self.tmp / "wrong_headers.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("foo,bar\nx,y\n")
        rc, _, err = self._run(
            str(csv_path),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 1)
        self.assertIn("not found", err.lower())

    def test_missing_mapping_file_errors(self) -> None:
        rc, _, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(self.tmp / "nope.json"),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 2)
        self.assertIn("mapping not found", err)

    def test_missing_csv_path_errors(self) -> None:
        rc, _, err = self._run(
            str(self.tmp / "nope.csv"),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 2)
        self.assertIn("csv_path not found", err)

    def test_missing_source_in_mapping_errors_without_cli_override(self) -> None:
        mapping_path = self.tmp / "nosrc.json"
        mapping_path.write_text(
            json.dumps({"columns": {"title": "PLACEHOLDER_title"}}),
            encoding="utf-8",
        )
        csv_path = self.tmp / "data.csv"
        csv_path.write_text("PLACEHOLDER_title\nFoo\n", encoding="utf-8")
        rc, _, err = self._run(
            str(csv_path),
            "--mapping", str(mapping_path),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 1)
        self.assertIn("source", err.lower())

    def test_missing_archive_file_treated_as_empty(self) -> None:
        missing = self.tmp / "does_not_exist.csv"
        self.assertFalse(missing.exists())
        rc, out, err = self._run(
            str(ESBD_FIXTURE),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(missing),
        )
        self.assertEqual(rc, 0, err)
        self.assertIn("dupes:  0 (0 active, 0 archive)", out)
        self.assertEqual(len(_read_csv(self.active)), 3)

    def test_non_utf8_csv_returns_controlled_error_not_traceback(self) -> None:
        # Write a CSV containing cp1252-only bytes (smart-quote 0x91/0x92
        # in the title cell) that are invalid as UTF-8. Default decoding
        # (utf-8-sig) MUST surface as a controlled CLI error pointing the
        # operator at --encoding, not as a Python traceback. Re-running
        # with the suggested encoding MUST then succeed.
        csv_path = self.tmp / "cp1252.csv"
        csv_path.write_bytes(
            b"Solicitation #,Title,Agency,URL,Posted Date,Due Date,"
            b"Delivery Location,Class/Item,Notice Type\n"
            b"NUTF-001,\x91Smart Quote Title\x92,Some Agency,"
            b"https://example.invalid/n,05/01/2026,06/01/2026,"
            b"Austin,NIGP 71500,Solicitation\n"
        )

        # (a) Default utf-8-sig: controlled error, no write.
        rc, _, err = self._run(
            str(csv_path),
            "--mapping", str(ESBD_CONFIG),
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc, 1)
        self.assertIn("cannot decode", err)
        self.assertIn("--encoding", err)
        self.assertEqual(_read_csv(self.active), [])

        # (b) Operator follows the guidance and retries with cp1252:
        # ingestion succeeds and the row lands in the active pipeline.
        rc2, _, err2 = self._run(
            str(csv_path),
            "--mapping", str(ESBD_CONFIG),
            "--encoding", "cp1252",
            "--active", str(self.active),
            "--archive", str(self.archive),
        )
        self.assertEqual(rc2, 0, err2)
        active_rows = _read_csv(self.active)
        self.assertEqual(len(active_rows), 1)
        self.assertEqual(active_rows[0]["solicitation_number"], "NUTF-001")
        self.assertIn("Smart Quote Title", active_rows[0]["title"])


if __name__ == "__main__":
    unittest.main()
