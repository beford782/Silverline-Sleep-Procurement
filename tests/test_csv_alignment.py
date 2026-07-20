"""Column-alignment guard for the tracked CSVs.

On 2026-07-17 a hand edit wrote an unquoted, comma-containing next_action into
bids/active/_pipeline.csv, silently shifting owner/created_date/notes/
procurement_risk/gate_status two fields to the right (found 2026-07-20). These
checks fail loudly on that class of corruption:

  1. Every raw row has exactly as many fields as the header.
  2. The pipeline gate columns only ever hold their known vocabulary, so a
     shift that happens to preserve the field count still gets caught.
"""

from __future__ import annotations

import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TRACKED_CSVS = [
    ROOT / "bids" / "active" / "_pipeline.csv",
    ROOT / "bids" / "archive" / "_pipeline_archive.csv",
    ROOT / "leads" / "review" / "_lead_radar.csv",
    ROOT / "leads" / "archive" / "_lead_radar_archive.csv",
    ROOT / "leads" / "demand" / "_demand_radar.csv",
    ROOT / "leads" / "demand" / "_demand_radar_archive.csv",
]

PIPELINE_CSVS = TRACKED_CSVS[:2]

GATE_STATUS_VOCAB = {"", "blocked", "bid_ready", "triage"}
PROCUREMENT_RISK_VOCAB = {"", "low", "medium", "high", "blocker"}


class CsvAlignmentTests(unittest.TestCase):
    def test_every_raw_row_matches_header_width(self) -> None:
        for path in TRACKED_CSVS:
            with self.subTest(csv=path.name):
                with path.open("r", encoding="utf-8", newline="") as fh:
                    reader = csv.reader(fh)
                    header = next(reader)
                    for lineno, row in enumerate(reader, start=2):
                        self.assertEqual(
                            len(row), len(header),
                            f"{path.name}:{lineno} has {len(row)} fields, "
                            f"header has {len(header)} — likely an unquoted "
                            f"comma (edit CSVs via csv.writer, never raw text)",
                        )

    def test_pipeline_gate_columns_hold_known_values(self) -> None:
        for path in PIPELINE_CSVS:
            with self.subTest(csv=path.name):
                with path.open("r", encoding="utf-8", newline="") as fh:
                    for row in csv.DictReader(fh):
                        rid = (row.get("opportunity_id") or "?")[:60]
                        self.assertIn(
                            (row.get("gate_status") or "").strip(),
                            GATE_STATUS_VOCAB,
                            f"{path.name} row {rid}: gate_status outside vocab "
                            f"— column shift or typo",
                        )
                        self.assertIn(
                            (row.get("procurement_risk") or "").strip(),
                            PROCUREMENT_RISK_VOCAB,
                            f"{path.name} row {rid}: procurement_risk outside "
                            f"vocab — column shift or typo",
                        )


if __name__ == "__main__":
    unittest.main()
