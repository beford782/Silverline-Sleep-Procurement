"""Unit tests for tools/lead_radar.py. Stdlib unittest, no network."""

from __future__ import annotations

import csv
import io
import json
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


class ClassifyLeadTypeTests(unittest.TestCase):
    def test_co_op_vehicle_terms(self) -> None:
        self.assertEqual(lead_radar.classify_lead_type("BuyBoard cooperative contract"),
                         "co-op_contract_vehicle")
        self.assertEqual(lead_radar.classify_lead_type("Sourcewell vendor pool IDIQ"),
                         "co-op_contract_vehicle")

    def test_furniture_ffe(self) -> None:
        self.assertEqual(lead_radar.classify_lead_type("School Furniture & Related Services"),
                         "broad_furniture_ffe")
        self.assertEqual(lead_radar.classify_lead_type("Institutional FF&E package"),
                         "broad_furniture_ffe")

    def test_vehicle_priority_over_generic_furniture(self) -> None:
        # A generic furniture buying vehicle keeps its vehicle-watch signal:
        # co-op/IDIQ/vendor-pool outranks plain furniture/FF&E.
        self.assertEqual(lead_radar.classify_lead_type("Office Furniture Catalog (IDIQ)"),
                         "co-op_contract_vehicle")
        self.assertEqual(lead_radar.classify_lead_type("Furniture vendor pool"),
                         "co-op_contract_vehicle")

    def test_specific_context_outranks_vehicle(self) -> None:
        # A specific institutional buyer cluster is more actionable than the
        # vehicle label, so it wins even when both appear.
        self.assertEqual(lead_radar.classify_lead_type("Residence hall furniture IDIQ"),
                         "dorm_student_housing")
        self.assertEqual(lead_radar.classify_lead_type("County jail furniture vendor pool"),
                         "correctional_detention")
        self.assertEqual(lead_radar.classify_lead_type("Emergency shelter supplies cooperative"),
                         "shelter_emergency")
        self.assertEqual(
            lead_radar.classify_lead_type("Behavioral health residential furniture cooperative"),
            "public_health_residential")

    def test_institutional_contexts(self) -> None:
        self.assertEqual(lead_radar.classify_lead_type("Residence hall move-in supplies"),
                         "dorm_student_housing")
        self.assertEqual(lead_radar.classify_lead_type("County jail inmate intake kits"),
                         "correctional_detention")
        self.assertEqual(lead_radar.classify_lead_type("Emergency disaster shelter cots"),
                         "shelter_emergency")
        self.assertEqual(lead_radar.classify_lead_type("Behavioral health residential care beds"),
                         "public_health_residential")

    def test_word_boundary_no_false_positive(self) -> None:
        # 'cot' must not fire inside 'Scott'; no family matches -> 'other'.
        self.assertEqual(lead_radar.classify_lead_type("Scott County paving project"), "other")

    def test_unmatched_is_other(self) -> None:
        self.assertEqual(lead_radar.classify_lead_type("Annual fireworks display"), "other")


class BuildLeadRowTests(unittest.TestCase):
    def _verdict(self):
        # Minimal stand-in shaped like relevance.Verdict.
        class V:
            matched_include = ["furniture", "ff&e"]
            reasons = ["weak only: furniture (no explicit mattress term)"]
        return V()

    def test_maps_opportunity_fields(self) -> None:
        opp = {
            "source": "IonWave", "buyer": "", "solicitation_number": "RFP 16.26",
            "title": "School Furniture & Related Services",
            "portal_url": "https://esc6emkt.ionwave.net/x",
            "posted_date": "2026-05-01", "due_date": "2026-06-05",
            "fit_score": "40", "commodity_terms": "",
        }
        lead = lead_radar.build_lead_row(opp, self._verdict(), "2026-06-18")
        self.assertEqual(set(lead), set(lead_radar.LEAD_HEADER))
        self.assertEqual(lead["status"], "reviewing")
        self.assertEqual(lead["source"], "IonWave")
        self.assertEqual(lead["solicitation_number"], "RFP 16.26")
        self.assertEqual(lead["due_date"], "2026-06-05")
        self.assertEqual(lead["fit_score"], "40")
        self.assertEqual(lead["lead_type"], "broad_furniture_ffe")
        self.assertIn("furniture", lead["trigger_terms"])
        self.assertTrue(lead["next_action"].startswith("HUMAN:"))
        self.assertEqual(lead["created_date"], "2026-06-18")
        # lead_id matches the canonical promote-time opportunity_id rule.
        self.assertEqual(
            lead["lead_id"],
            pipeline.derive_opportunity_id("IonWave", "", "RFP 16.26",
                                           "School Furniture & Related Services"),
        )

    def test_lead_matches_active_row_by_keys(self) -> None:
        # A lead and an active-pipeline row for the same opportunity share a
        # dedup key, even though they store different id columns.
        opp = {"source": "IonWave", "buyer": "", "solicitation_number": "RFP 16.26",
               "title": "School Furniture & Related Services"}
        lead = lead_radar.build_lead_row(opp, None, "2026-06-18")
        active_like = {"source": "IonWave", "solicitation_number": "RFP 16.26",
                       "title": "School Furniture & Related Services"}
        self.assertTrue(lead_radar.lead_match_keys(lead) & lead_radar.lead_match_keys(active_like))


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


class CalendarUnitTests(unittest.TestCase):
    """Pure helpers: lead-time classes, candidate selection, event math."""

    def _row(self, **over: str) -> dict:
        row = {k: "" for k in lead_radar.LEAD_HEADER}
        row.update(over)
        return row

    def test_lead_time_coop_180(self) -> None:
        for source, buyer in [
            ("BuyBoard", "TASB / BuyBoard"), ("TIPS", "Region 8 ESC / TIPS"),
            ("Sourcewell", "Sourcewell"), ("OMNIA Partners", "Region 4 ESC / OMNIA"),
            ("Choice Partners / HCDE", "Harris County"), ("E&I Cooperative Services", "E&I"),
        ]:
            row = self._row(source=source, buyer=buyer)
            self.assertEqual(lead_radar.calendar_lead_time_days(row), 180,
                             f"{source!r} should be a 180-day co-op class")

    def test_lead_time_federal_60(self) -> None:
        row = self._row(source="SAM.gov (federal)", buyer="U.S. DOJ",
                        solicitation_number="recurring (ex. X)")
        self.assertEqual(lead_radar.calendar_lead_time_days(row), 60)

    def test_lead_time_default_120(self) -> None:
        row = self._row(source="LaPAC", buyer="State of Louisiana")
        self.assertEqual(lead_radar.calendar_lead_time_days(row), 120)

    def test_candidate_selection(self) -> None:
        self.assertTrue(lead_radar.is_calendar_candidate(
            self._row(lead_type="awarded_contract_watch")))
        self.assertTrue(lead_radar.is_calendar_candidate(
            self._row(source="SAM.gov (federal)", solicitation_number="recurring (ex. X)",
                      lead_type="correctional_detention")))
        self.assertFalse(lead_radar.is_calendar_candidate(
            self._row(lead_type="co-op_contract_vehicle")))

    def test_build_event_math(self) -> None:
        row = self._row(
            lead_id="sw-1", source="Sourcewell", buyer="Sourcewell",
            solicitation_number="RFP 091423", title="Furniture Solutions",
            due_date="2027-12-04", fit_score="45",
            portal_url="https://example.test/sw",
        )
        ev = lead_radar.build_event(row, date(2026, 6, 28))
        self.assertEqual(ev["lead_time_days"], 180)
        self.assertEqual(ev["start"], "2027-06-07")  # 2027-12-04 - 180d
        self.assertEqual(ev["expiry"], "2027-12-04")
        self.assertEqual(ev["key"], "sw-1:2027-12-04")
        self.assertFalse(ev["overdue"])
        self.assertIn("[Re-bid prep]", ev["title"])
        # description carries the prep-checklist ladder + portal + fit + expiry.
        for step in lead_radar.PREP_CHECKLIST:
            self.assertIn(step, ev["description"])
        self.assertIn("https://example.test/sw", ev["description"])
        self.assertIn("Fit score: 45", ev["description"])
        self.assertIn("2027-12-04", ev["description"])

    def test_blank_expiry_warns_no_event(self) -> None:
        rows = [self._row(lead_id="choice-1", source="Choice Partners / HCDE",
                          buyer="HCDE", solicitation_number="23/022MF",
                          title="FF&E", lead_type="awarded_contract_watch",
                          due_date="")]
        payload = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 1825)
        self.assertEqual(payload["events"], [])
        self.assertEqual(len(payload["warnings"]), 1)
        self.assertEqual(payload["warnings"][0]["lead_id"], "choice-1")
        self.assertIn("expiry unknown", payload["warnings"][0]["message"])

    def test_build_payload_deterministic_and_sorted(self) -> None:
        rows = [
            self._row(lead_id="b", source="BuyBoard", buyer="BuyBoard",
                      solicitation_number="767-25", title="Furniture",
                      lead_type="awarded_contract_watch", due_date="2028-03-31"),
            self._row(lead_id="a", source="Sourcewell", buyer="Sourcewell",
                      solicitation_number="091423", title="Furniture",
                      lead_type="awarded_contract_watch", due_date="2027-12-04"),
        ]
        p1 = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 1825)
        p2 = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 1825)
        self.assertEqual(p1, p2)  # pure / deterministic
        # sorted by prep_window (start) ascending: Sourcewell 2027-06-07 first.
        self.assertEqual([e["start"] for e in p1["events"]], ["2027-06-07", "2027-10-03"])
        self.assertEqual([e["lead_id"] for e in p1["events"]], ["a", "b"])

    def test_idempotency_already_scheduled(self) -> None:
        rows = [
            self._row(lead_id="a", source="Sourcewell", buyer="Sourcewell",
                      solicitation_number="091423", title="Furniture",
                      lead_type="awarded_contract_watch", due_date="2027-12-04"),
            self._row(lead_id="b", source="BuyBoard", buyer="BuyBoard",
                      solicitation_number="767-25", title="Furniture",
                      lead_type="awarded_contract_watch", due_date="2028-03-31"),
        ]
        state = {"a:2027-12-04": {"event_id": "evt_123", "created": "2026-06-28"}}
        payload = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 1825, state)
        by_id = {e["lead_id"]: e for e in payload["events"]}
        self.assertTrue(by_id["a"]["already_scheduled"])
        self.assertFalse(by_id["b"]["already_scheduled"])

    def test_horizon_filtering_and_overdue_inclusion(self) -> None:
        rows = [
            # prep_window 2026-02-09 (past) -> OVERDUE, always included.
            self._row(lead_id="past", source="LaPAC", buyer="State of Louisiana",
                      solicitation_number="x", title="Mattresses",
                      lead_type="awarded_contract_watch", due_date="2026-06-09"),
            # prep_window 2031-03-04 -> beyond a short horizon, excluded.
            self._row(lead_id="far", source="OMNIA Partners", buyer="OMNIA",
                      solicitation_number="y", title="Mattresses",
                      lead_type="awarded_contract_watch", due_date="2031-08-31"),
        ]
        # 1-year horizon: 'far' excluded, 'past' (overdue) still present.
        payload = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 365)
        ids = [e["lead_id"] for e in payload["events"]]
        self.assertIn("past", ids)
        self.assertNotIn("far", ids)
        self.assertTrue(next(e for e in payload["events"] if e["lead_id"] == "past")["overdue"])
        # 5-year horizon: both present.
        wide = lead_radar.build_calendar_payload(rows, date(2026, 6, 28), 1825)
        self.assertEqual({e["lead_id"] for e in wide["events"]}, {"past", "far"})


class CalendarRealRowTests(unittest.TestCase):
    """The six committed re-bid rows produce the right prep windows."""

    def setUp(self) -> None:
        _, self.rows = lead_radar.read_lead_rows(lead_radar.DEFAULT_REVIEW)
        self.payload = lead_radar.build_calendar_payload(self.rows, date(2026, 6, 28), 1825)
        self.by_id = {e["lead_id"]: e for e in self.payload["events"]}

    def test_real_prep_windows(self) -> None:
        expected = {
            "sourcewell-sourcewell-member-agencies-rfp-091423": ("2027-12-04", "2027-06-07", 180),
            "buyboard-tasb-buyboard-member-agencies-proposal-767-25": ("2028-03-31", "2027-10-03", 180),
            "tips-region-8-esc-tips-member-agencies-tips-230301": ("2028-05-31", "2027-12-03", 180),
            "omnia-partners-region-4-esc-lead-agency-omnia-region-4-dorm-furniture": ("2029-09-30", "2029-04-03", 180),
            "omnia-partners-omnia-uc-lead-agency-omnia-mattresses-master": ("2031-08-31", "2031-03-04", 180),
        }
        for lead_id, (expiry, start, lt) in expected.items():
            self.assertIn(lead_id, self.by_id, f"missing event for {lead_id}")
            ev = self.by_id[lead_id]
            self.assertEqual(ev["expiry"], expiry)
            self.assertEqual(ev["start"], start)
            self.assertEqual(ev["lead_time_days"], lt)

    def test_choice_row_warns_only(self) -> None:
        choice = "choice-partners-hcde-harris-county-dept-of-education-23-022mf"
        self.assertNotIn(choice, self.by_id)
        warn_ids = {w["lead_id"] for w in self.payload["warnings"]}
        self.assertIn(choice, warn_ids)


class CalendarCliTests(_CliCase):
    """CLI emit: writes JSON, no network/state mutation, --stdout works."""

    def _add_awarded(self, lead_id_sol: str, due: str) -> None:
        self.add_lead(source="Sourcewell", buyer="Sourcewell",
                      title="Furniture Solutions",
                      solicitation_number=lead_id_sol, due_date=due,
                      lead_type="awarded_contract_watch")

    def _cal_base(self, tmp) -> list[str]:
        return self._base() + [
            "calendar", "--today", "2026-06-28",
            "--out", str(tmp / "events.json"),
            "--state", str(tmp / "state.json"),
        ]

    def test_emit_writes_json_file(self) -> None:
        self._add_awarded("091423", "2027-12-04")
        tmp = Path(self._tmp.name)
        rc, out = self.run_cli(*self._cal_base(tmp))
        self.assertEqual(rc, 0)
        events_path = tmp / "events.json"
        self.assertTrue(events_path.exists())
        # No state file is created by emit (read-only ledger access).
        self.assertFalse((tmp / "state.json").exists())
        payload = json.loads(events_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["horizon_days"], 1825)
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["start"], "2027-06-07")
        self.assertIn("Re-bid prep windows", out)

    def test_emit_stdout_does_not_write_file(self) -> None:
        self._add_awarded("091423", "2027-12-04")
        tmp = Path(self._tmp.name)
        rc, out = self.run_cli(*self._cal_base(tmp), "--stdout")
        self.assertEqual(rc, 0)
        self.assertFalse((tmp / "events.json").exists())
        # JSON is present in stdout after the table.
        json_text = out[out.index("{"):]
        payload = json.loads(json_text)
        self.assertEqual(payload["events"][0]["start"], "2027-06-07")

    def test_emit_marks_already_scheduled_from_state(self) -> None:
        self._add_awarded("091423", "2027-12-04")
        tmp = Path(self._tmp.name)
        # lead_id is derived by `add`; read it back to build the state key.
        lead_id = self.review_rows()[0]["lead_id"]
        (tmp / "state.json").write_text(
            json.dumps({f"{lead_id}:2027-12-04": {"event_id": "evt_9", "created": "2026-06-28"}}),
            encoding="utf-8",
        )
        rc, _ = self.run_cli(*self._cal_base(tmp))
        self.assertEqual(rc, 0)
        payload = json.loads((tmp / "events.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["events"][0]["already_scheduled"])


if __name__ == "__main__":
    unittest.main()
