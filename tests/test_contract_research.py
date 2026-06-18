"""Tests for committed contract research trackers."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "sources" / "txsmartbuy_contract_research.csv"


class TxSmartBuyContractResearchTests(unittest.TestCase):
    def test_tracker_has_expected_shape(self) -> None:
        with TRACKER.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
        self.assertEqual(reader.fieldnames, [
            "source",
            "contract",
            "description",
            "contract_type",
            "contract_group",
            "start_date",
            "end_date",
            "renewal_watch_date",
            "nigp_codes",
            "fed_schedule",
            "relevance",
            "operator_notes",
        ])
        self.assertNotIn("due_date", reader.fieldnames)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["source"] == "Texas SmartBuy Contracts" for r in rows))

    def test_dates_are_iso_and_notes_keep_rows_out_of_active_pipeline(self) -> None:
        with TRACKER.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            for field in ("start_date", "end_date", "renewal_watch_date"):
                datetime.strptime(row[field], "%Y-%m-%d")
            self.assertIn("not an open solicitation", row["operator_notes"].lower())

    def test_expected_mattress_nigp_codes_are_captured(self) -> None:
        with TRACKER.open("r", encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        all_codes = set()
        for row in rows:
            all_codes.update(code.strip() for code in row["nigp_codes"].split(";") if code.strip())
        for expected in ("42024", "42060", "42062", "42068", "85084", "56535"):
            self.assertIn(expected, all_codes)


if __name__ == "__main__":
    unittest.main()
