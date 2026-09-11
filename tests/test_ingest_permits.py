"""Unit tests for tools/ingest_permits.py (Austin Socrata permit adapter).

Stdlib unittest, fixture-driven, no network. The fixture is 20 real records
from data.austintexas.gov/resource/3syk-w9eu.json (contractor person/phone/
address fields stripped) chosen to cover: the 311 E 5TH ST hotel floor set
(3 BP + a PP sibling), the UT Law Student Housing EP, an assisted-living
Demolition BP, two generator-replacement BPs, the 400 LAVACA ST hotel EP/PP
siblings, a hotel parking-garage BP, a re-roof BP, the TECH RIDGE BLVD hotel
pool PP, the 808 EBERHART LN senior-living BP set across buildings, and a
hotel blade-sign EP.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import demand_radar  # noqa: E402
import ingest_permits  # noqa: E402
import pii_lint  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "austin_permits_sample.json"
CONFIG = ROOT / "configs" / "permits.json"
TODAY = "2026-09-11"


def _records() -> list[dict]:
    with FIXTURE.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _source() -> dict:
    return ingest_permits.load_config(CONFIG)[0]


def _run_main(argv: list[str]) -> tuple[int, str]:
    out = io.StringIO()
    with redirect_stdout(out), redirect_stderr(io.StringIO()):
        rc = ingest_permits.main(argv)
    return rc, out.getvalue()


def _fixture_rows(src: dict | None = None) -> dict:
    src = src or _source()
    return ingest_permits.ingest_source(_records(), src, TODAY, set())


def _make_record(**over) -> dict:
    rec = {
        "permit_number": "2026-900001 BP", "permittype": "BP",
        "permit_type_desc": "Building Permit", "permit_class_mapped": "Commercial",
        "work_class": "Remodel", "description": "Hotel guestroom renovation",
        "permit_location": "100 CONGRESS AVE", "original_address1": "100 CONGRESS AVE",
        "original_city": "AUSTIN", "original_state": "TX", "original_zip": "78701",
        "applieddate": "2026-06-01T00:00:00.000", "issue_date": "2026-08-20T00:00:00.000",
        "status_current": "Active", "housing_units": "1", "number_of_floors": "3",
        "project_id": "99000001", "masterpermitnum": "99000000",
        "contractor_company_name": "Example Builders LLC  *MAIN**",
        "link": {"url": "https://abc.austintexas.gov/web/permit/public-search-other?t_detail=1&t_selected_folderrsn=99000001"},
    }
    rec.update(over)
    return rec


class ConfigTests(unittest.TestCase):
    def test_committed_config_loads_and_is_socrata_bp_only(self) -> None:
        cfg = ingest_permits.load_config(CONFIG)
        self.assertEqual(len(cfg), 1)
        src = cfg[0]
        self.assertEqual(src["adapter"], "socrata")
        self.assertEqual(src["permit_types"], ["BP"])
        self.assertIn("Demolition", src["exclude_work_class"])
        self.assertIn("generator", src["exclude_terms"])
        self.assertEqual((src["city"], src["state"]), ("Austin", "TX"))

    def test_config_requires_url_and_source(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "permits.json"
            bad.write_text('[{"source": "X"}]', encoding="utf-8")
            with self.assertRaises(ValueError):
                ingest_permits.load_config(bad)


class SoqlUrlTests(unittest.TestCase):
    def _params(self, src: dict, since: str) -> dict:
        url = ingest_permits.build_socrata_url(src, since)
        split = urllib.parse.urlsplit(url)
        self.assertEqual(split.scheme + "://" + split.netloc + split.path, src["url"])
        return {k: v[0] for k, v in urllib.parse.parse_qs(split.query).items()}

    def test_where_clause_carries_since_type_class_and_keywords(self) -> None:
        p = self._params(_source(), "2026-08-28")
        where = p["$where"]
        self.assertIn("issue_date > '2026-08-28T00:00:00'", where)
        self.assertIn("permit_class_mapped = 'Commercial'", where)
        self.assertIn("permittype in ('BP')", where)
        self.assertIn("upper(description) LIKE '%HOTEL%'", where)
        self.assertIn("upper(description) LIKE '%ASSISTED LIVING%'", where)
        self.assertIn(" OR ", where)
        self.assertEqual(p["$order"], "issue_date DESC")
        self.assertEqual(p["$limit"], "500")

    def test_select_never_requests_contractor_pii(self) -> None:
        p = self._params(_source(), "2026-08-28")
        select = p["$select"]
        for forbidden in ingest_permits.FORBIDDEN_FIELDS:
            self.assertNotIn(forbidden, select)
        self.assertNotIn("contractor_phone", ingest_permits.build_socrata_url(_source(), "2026-08-28"))
        for needed in ("permit_number", "permittype", "work_class", "description",
                       "original_address1", "issue_date", "masterpermitnum", "link",
                       "contractor_company_name"):
            self.assertIn(needed, select)

    def test_single_quotes_in_keywords_are_escaped(self) -> None:
        src = dict(_source(), keywords=["children's home"])
        p = self._params(src, "2026-01-01")
        self.assertIn("LIKE '%CHILDREN''S HOME%'", p["$where"])

    def test_limit_from_config(self) -> None:
        p = self._params(dict(_source(), limit=50), "2026-01-01")
        self.assertEqual(p["$limit"], "50")


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = _source()
        self.kept, self.rejected = ingest_permits.filter_records(_records(), self.src, TODAY)
        self.reasons = {(r["permit_number"], r["reason"]) for r in self.rejected}

    def test_non_bp_trade_siblings_are_rejected(self) -> None:
        self.assertIn(("2026-111105 EP", "non_bp:EP"), self.reasons)   # UT Law Student Housing EP
        self.assertIn(("2025-141480 PP", "non_bp:PP"), self.reasons)   # 311 E 5TH pool PP
        self.assertIn(("2016-124504 PP", "non_bp:PP"), self.reasons)   # TECH RIDGE hotel pool PP
        self.assertIn(("2026-046292 EP", "non_bp:EP"), self.reasons)   # 400 LAVACA hotel EP
        self.assertTrue(all(r["permittype"] == "BP" for r in self.kept))

    def test_demolition_is_rejected_by_work_class(self) -> None:
        self.assertIn(("2026-103102 BP", "work_class_excluded:Demolition"), self.reasons)

    def test_exclude_terms_send_generator_to_rejects(self) -> None:
        self.assertIn(("2026-082819 BP", "exclude_term:generator"), self.reasons)
        self.assertIn(("2026-097374 BP", "exclude_term:generator"), self.reasons)
        self.assertIn(("2026-098841 BP", "exclude_term:parking garage"), self.reasons)
        self.assertIn(("2026-088774 BP", "exclude_term:roof"), self.reasons)

    def test_exclude_terms_match_whole_words(self) -> None:
        rec = _make_record(description="Hotel guestroom waterproofing and fireproofing repairs")
        kept, rejected = ingest_permits.filter_records([rec], self.src, TODAY)
        self.assertEqual(len(kept), 1, "'roof' must not fire inside 'waterproofing'")
        self.assertEqual(rejected, [])

    def test_reject_rows_carry_the_reject_schema(self) -> None:
        for r in self.rejected:
            self.assertEqual(list(r.keys()), ingest_permits.REJECT_HEADER)
            self.assertEqual(r["rejected_date"], TODAY)
            self.assertLessEqual(len(r["description"]), 160)
            self.assertNotIn("\n", r["description"])

    def test_survivors_are_the_seven_project_bps(self) -> None:
        self.assertEqual(len(self.kept), 7)
        self.assertEqual(len(self.rejected), 13)


class GroupingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.src = _source()
        self.result = _fixture_rows(self.src)
        self.rows = {r["location"]: r for r in self.result["accepted"]}

    def test_fixture_collapses_to_three_signals(self) -> None:
        self.assertEqual(self.result["fetched"], 20)
        self.assertEqual(self.result["grouped"], 3)
        self.assertEqual(len(self.result["accepted"]), 3)
        self.assertEqual(self.result["duplicates"], 0)

    def test_hotel_floor_set_is_one_row(self) -> None:
        row = self.rows["311 E 5TH ST, Austin, TX 78701"]
        self.assertEqual(row["segment"], "hotel")
        self.assertEqual(row["facility_name"],
                         "Hotel permit: Finish Out for Hotel Rooms Housekeeping Hydration station and Electrical/IDF Room")
        self.assertIn("permits: 2024-128983 BP, 2024-128984 BP, 2024-128986 BP (3 BP, master 13190708)", row["notes"])
        self.assertIn("floors: 11, 12, 14", row["notes"])
        self.assertIn("work_class: Remodel", row["notes"])
        self.assertIn("applied 2023-08-10, issued 2026-08-10", row["notes"])
        self.assertIn("GC: DPR Construction", row["notes"])
        self.assertNotIn("MAIN", row["notes"])
        self.assertEqual(row["source_url"],
                         "https://abc.austintexas.gov/web/permit/public-search-other?t_detail=1&t_selected_folderrsn=13405039")
        self.assertEqual(row["signal_source"], "Permits: City of Austin")
        self.assertEqual(row["status"], "reviewing")
        self.assertEqual(row["owner_operator"], "")

    def test_senior_living_buildings_group_by_address_stem(self) -> None:
        row = self.rows["808 EBERHART LN, Austin, TX 78745"]
        self.assertEqual(row["segment"], "senior-living")
        self.assertIn("(3 BP, master 13688613)", row["notes"])
        self.assertIn("site units: BLDG 100, BLDG 500, BLDG 900", row["notes"])

    def test_stage_derived_from_work_class_when_classifier_is_silent(self) -> None:
        row = self.rows["311 E 5TH ST, Austin, TX 78701"]
        self.assertEqual(row["project_stage"], "renovation")
        self.assertIn("stage derived from work_class Remodel", row["notes"])

    def test_classifier_reject_is_downgraded_to_review_not_dropped(self) -> None:
        # "shelter" alone is not in the classifier lexicon (it wants "homeless
        # shelter"), so the classifier says REJECT; the permit is kept anyway.
        rec = _make_record(description="Interior build-out of new shelter wing with 40 beds",
                           work_class="New")
        res = ingest_permits.ingest_source([rec], self.src, TODAY, set())
        self.assertEqual(len(res["accepted"]), 1)
        row = res["accepted"][0]
        self.assertEqual(row["status"], "reviewing")
        self.assertIn("classifier=REJECT, kept as permit signal", row["notes"])
        self.assertTrue(row["segment"])  # falls back to the matched keyword's segment
        self.assertEqual(row["project_stage"], "under-construction")

    def test_location_keeps_uppercase_site_and_appends_city_state_zip(self) -> None:
        self.assertIn("311 E 5TH ST, Austin, TX 78701", self.rows)
        self.assertIn("4100 JACKSON AVE, Austin, TX 78731", self.rows)
        for loc in self.rows:
            self.assertNotIn("5th St", loc)  # never title-cased

    def test_facility_name_is_single_line_and_bounded(self) -> None:
        long_desc = ("Hotel " + "renovation of guestrooms corridors and public areas " * 6
                     + "\nsecond line\r\nthird line")
        res = ingest_permits.ingest_source([_make_record(description=long_desc)], self.src, TODAY, set())
        name = res["accepted"][0]["facility_name"]
        self.assertNotIn("\n", name)
        self.assertNotIn("\r", name)
        self.assertLessEqual(len(name), 110)
        self.assertTrue(name.startswith("Hotel permit: "))
        for row in self.rows.values():
            self.assertNotIn("\n", row["facility_name"])
            self.assertLessEqual(len(row["facility_name"]), 110)

    def test_demand_id_is_stable_and_matches_derived_key(self) -> None:
        for row in self.rows.values():
            derived = demand_radar.demand_id_for(row["signal_source"], row["segment"],
                                                 row["facility_name"], row["location"])
            self.assertEqual(row["demand_id"], derived)
        again = {r["demand_id"] for r in _fixture_rows(self.src)["accepted"]}
        self.assertEqual(again, {r["demand_id"] for r in self.rows.values()})

    def test_est_value_from_valuation_only_when_positive(self) -> None:
        res = ingest_permits.ingest_source(
            [_make_record(total_job_valuation="27700")], self.src, TODAY, set())
        self.assertEqual(res["accepted"][0]["est_value"], "27700")
        res = ingest_permits.ingest_source(
            [_make_record(total_job_valuation=None)], self.src, TODAY, set())
        self.assertEqual(res["accepted"][0]["est_value"], "")

    def test_case_number_year_is_not_a_completion_date(self) -> None:
        rec = _make_record(description="Hotel guestroom remodel. SP-2026-0151C.SH - Approved")
        row = ingest_permits.ingest_source([rec], self.src, TODAY, set())["accepted"][0]
        self.assertEqual(row["est_completion_date"], "")
        self.assertEqual(row["est_buy_window"], "2026-11")  # issued 2026-08-20 + 3 months
        self.assertIn("buy-window derived from permit issue date", row["notes"])


class DerivationTests(unittest.TestCase):
    def test_stage_from_work_class(self) -> None:
        self.assertEqual(ingest_permits.stage_from_work_class("New"), "under-construction")
        self.assertEqual(ingest_permits.stage_from_work_class("Addition and Remodel"), "under-construction")
        for wc in ("Remodel", "Upgrade", "Projecting", "Repair"):
            self.assertEqual(ingest_permits.stage_from_work_class(wc), "renovation", wc)
        self.assertEqual(ingest_permits.stage_from_work_class(""), "")

    def test_buy_window_offsets_and_year_rollover(self) -> None:
        self.assertEqual(ingest_permits.derive_buy_window("2026-08-10", "Remodel"), "2026-11")
        self.assertEqual(ingest_permits.derive_buy_window("2026-11-20", "Remodel"), "2027-02")
        self.assertEqual(ingest_permits.derive_buy_window("2026-08-10", "New"), "2027-11")
        self.assertEqual(ingest_permits.derive_buy_window("2026-11-20", "New"), "2028-02")
        self.assertEqual(ingest_permits.derive_buy_window("2026-12-31", "Upgrade"), "2027-03")
        self.assertEqual(ingest_permits.derive_buy_window("", "New"), "")

    def test_add_months(self) -> None:
        self.assertEqual(ingest_permits.add_months("2026-01-15", 0), "2026-01")
        self.assertEqual(ingest_permits.add_months("2026-10-01", 15), "2028-01")

    def test_description_stem_strips_trailing_floor(self) -> None:
        self.assertEqual(ingest_permits.description_stem("Finish Out for Hotel Rooms  Floor 11"),
                         "Finish Out for Hotel Rooms")
        self.assertEqual(ingest_permits.description_stem("Hotel lobby - Level 3"), "Hotel lobby")
        self.assertEqual(ingest_permits.floors_in("Rooms Floor 11 and floor 12"), ["11", "12"])

    def test_address_stem_and_contractor_cleanup(self) -> None:
        self.assertEqual(ingest_permits.address_stem("808 EBERHART LN BLDG 100"), "808 EBERHART LN")
        self.assertEqual(ingest_permits.address_stem("2902 MEDICAL ARTS ST BLDG TNFM1"), "2902 MEDICAL ARTS ST")
        self.assertEqual(ingest_permits.address_stem("311 E 5TH ST"), "311 E 5TH ST")
        self.assertEqual(ingest_permits.clean_contractor("DPR Construction  *MAIN**"), "DPR Construction")
        self.assertEqual(ingest_permits.clean_contractor("Power Design Inc****MAIN***"), "Power Design Inc")
        self.assertEqual(ingest_permits.clean_contractor("Westminster Manor"), "Westminster Manor")


class PiiTests(unittest.TestCase):
    def test_generated_rows_pass_pii_lint(self) -> None:
        rows = _fixture_rows()["accepted"]
        with tempfile.TemporaryDirectory() as d:
            csv_path = Path(d) / "demand.csv"
            demand_radar.write_demand_rows_atomic(csv_path, rows)
            self.assertEqual(pii_lint.scan_file(csv_path, set(pii_lint.PUBLIC_ALLOWLIST)), [])
            out = io.StringIO()
            with redirect_stdout(out):
                rc = pii_lint.main([str(csv_path)])
            self.assertEqual(rc, 0, out.getvalue())

    def test_title_case_address_and_phone_in_description_are_scrubbed(self) -> None:
        rec = _make_record(description="Hotel renovation at 400 Lavaca Street, call 512-555-1234 or EIN 12-3456789")
        row = ingest_permits.ingest_source([rec], _source(), TODAY, set())["accepted"][0]
        self.assertIn("400 LAVACA STREET", row["facility_name"])
        self.assertNotIn("Lavaca Street", row["facility_name"])
        self.assertNotIn("512-555-1234", row["facility_name"])
        for text in (row["facility_name"], row["notes"]):
            self.assertEqual(pii_lint.scan_text(text, set()), [], text)

    def test_no_contractor_person_fields_survive_in_fixture_or_rows(self) -> None:
        for rec in _records():
            for forbidden in ingest_permits.FORBIDDEN_FIELDS:
                self.assertNotIn(forbidden, rec)
        for row in _fixture_rows()["accepted"]:
            self.assertNotIn("MAIN", row["notes"])


class CliTests(unittest.TestCase):
    def test_fixture_dry_run_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            demand_csv = Path(d) / "demand.csv"
            reject_csv = Path(d) / "rejects.csv"
            rc, out = _run_main(["--config", str(CONFIG), "--fixture", str(FIXTURE),
                                 "--demand", str(demand_csv),
                                 "--demand-archive", str(Path(d) / "archive.csv"),
                                 "--reject-log", str(reject_csv),
                                 "--today", TODAY, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("dry run, nothing written", out)
            self.assertIn("accepted 3", out)
            self.assertIn("311 E 5TH ST".lower().replace(" ", "-"), out)
            self.assertFalse(demand_csv.exists())
            self.assertFalse(reject_csv.exists())

    def test_second_pass_over_same_fixture_adds_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            demand_csv = Path(d) / "demand.csv"
            reject_csv = Path(d) / "rejects.csv"
            base = ["--config", str(CONFIG), "--fixture", str(FIXTURE),
                    "--demand", str(demand_csv),
                    "--demand-archive", str(Path(d) / "archive.csv"),
                    "--reject-log", str(reject_csv)]
            rc, out = _run_main(base + ["--today", TODAY])
            self.assertEqual(rc, 0)
            self.assertIn("wrote 3 demand signal(s)", out)
            _, rows = demand_radar.read_demand_rows(demand_csv)
            self.assertEqual(len(rows), 3)
            first_ids = [r["demand_id"] for r in rows]

            # Two weeks later the lookback window still covers the same permits.
            rc2, out2 = _run_main(base + ["--today", "2026-09-25"])
            self.assertEqual(rc2, 0)
            self.assertIn("accepted 0", out2)
            self.assertIn("duplicate 3", out2)
            self.assertIn("(no new rows to write)", out2)
            _, rows2 = demand_radar.read_demand_rows(demand_csv)
            self.assertEqual([r["demand_id"] for r in rows2], first_ids)

            # Reject log: header once, appended across runs, duplicates recorded.
            with reject_csv.open("r", encoding="utf-8", newline="") as fh:
                lines = list(csv.reader(fh))
            self.assertEqual(lines[0], ingest_permits.REJECT_HEADER)
            self.assertEqual(sum(1 for ln in lines if ln == ingest_permits.REJECT_HEADER), 1)
            self.assertEqual(len(lines) - 1, 13 + 13 + 3)
            reasons = [ln[5] for ln in lines[1:]]
            self.assertEqual(reasons.count("duplicate"), 3)
            self.assertIn("exclude_term:generator", reasons)

    def test_archive_row_blocks_reingest(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            demand_csv = Path(d) / "demand.csv"
            archive_csv = Path(d) / "archive.csv"
            rows = _fixture_rows()["accepted"]
            demand_radar.write_demand_rows_atomic(archive_csv, rows[:1])
            rc, out = _run_main(["--config", str(CONFIG), "--fixture", str(FIXTURE),
                                 "--demand", str(demand_csv), "--demand-archive", str(archive_csv),
                                 "--today", TODAY])
            self.assertEqual(rc, 0)
            self.assertIn("accepted 2", out)
            self.assertIn("duplicate 1", out)
            _, written = demand_radar.read_demand_rows(demand_csv)
            self.assertEqual(len(written), 2)
            self.assertNotIn(rows[0]["demand_id"], {r["demand_id"] for r in written})

    def test_output_lists_each_new_row(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            rc, out = _run_main(["--config", str(CONFIG), "--fixture", str(FIXTURE),
                                 "--demand", str(Path(d) / "demand.csv"),
                                 "--demand-archive", str(Path(d) / "archive.csv"),
                                 "--today", TODAY, "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("| Hotel permit: Finish Out for Hotel Rooms", out)
            self.assertIn("| buy-window 2026-11", out)
            self.assertIn("since 2026-08-28", out)  # 14-day lookback from --today

    def test_since_days_override(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            rc, out = _run_main(["--config", str(CONFIG), "--fixture", str(FIXTURE),
                                 "--demand", str(Path(d) / "demand.csv"),
                                 "--demand-archive", str(Path(d) / "archive.csv"),
                                 "--today", TODAY, "--since-days", "30", "--dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("since 2026-08-12", out)


class FailureTests(unittest.TestCase):
    """A fetch failure must never look like a quiet day."""

    def _cfg(self, d: str, **over) -> Path:
        src = dict(_source(), **over)
        cfg = Path(d) / "permits.json"
        cfg.write_text(json.dumps([src]), encoding="utf-8")
        return cfg

    def test_fetch_exception_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d)
            with mock.patch.object(ingest_permits, "fetch_json",
                                   side_effect=urllib.error.URLError("timed out")):
                rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                     "--demand-archive", str(Path(d) / "archive.csv"),
                                     "--today", TODAY, "--dry-run"])
            self.assertNotEqual(rc, 0)
            self.assertIn("::warning::permit source FAILED: Permits: City of Austin", out)
            self.assertIn("timed out", out)

    def test_http_error_returns_nonzero_and_names_status(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d)
            err = urllib.error.HTTPError("https://x", 403, "Forbidden", {}, None)
            with mock.patch.object(ingest_permits, "fetch_json", side_effect=err):
                rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                     "--demand-archive", str(Path(d) / "archive.csv"), "--dry-run"])
            self.assertEqual(rc, 1)
            self.assertIn("HTTP 403", out)

    def test_bad_url_scheme_returns_nonzero_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d, url="not-a-url")
            rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                 "--demand-archive", str(Path(d) / "archive.csv"), "--dry-run"])
            self.assertNotEqual(rc, 0)
            self.assertIn("FAILED", out)

    def test_unknown_adapter_is_a_failure_not_a_skip(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d, adapter="ckan")
            rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                 "--demand-archive", str(Path(d) / "archive.csv"), "--dry-run"])
            self.assertNotEqual(rc, 0)
            self.assertIn("not implemented", out)

    def test_non_array_payload_is_a_parse_failure(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d)
            with mock.patch.object(ingest_permits, "fetch_json",
                                   side_effect=ValueError("expected a JSON array, got dict")):
                rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                     "--demand-archive", str(Path(d) / "archive.csv"), "--dry-run"])
            self.assertEqual(rc, 1)

    def test_mocked_success_path_exits_zero_with_no_new_rows(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            cfg = self._cfg(d)
            with mock.patch.object(ingest_permits, "fetch_json", return_value=[]):
                rc, out = _run_main(["--config", str(cfg), "--demand", str(Path(d) / "demand.csv"),
                                     "--demand-archive", str(Path(d) / "archive.csv"),
                                     "--today", TODAY])
            self.assertEqual(rc, 0)
            self.assertIn("fetched 0", out)
            self.assertIn("(no new rows to write)", out)

    def test_missing_config_returns_2(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            rc, _ = _run_main(["--config", str(Path(d) / "nope.json"), "--dry-run"])
            self.assertEqual(rc, 2)


class RejectLogTests(unittest.TestCase):
    def test_header_written_once_then_appended(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sub" / "rejects.csv"
            rows = _fixture_rows()["rejected"]
            ingest_permits.append_reject_log(path, rows[:2])
            ingest_permits.append_reject_log(path, rows[2:4])
            ingest_permits.append_reject_log(path, [])  # no-op
            with path.open("r", encoding="utf-8", newline="") as fh:
                lines = list(csv.reader(fh))
            self.assertEqual(lines[0], ingest_permits.REJECT_HEADER)
            self.assertEqual(len(lines), 5)
            self.assertEqual(lines[1][2], rows[0]["permit_number"])


class SubprocessSmokeTests(unittest.TestCase):
    def test_cli_fixture_dry_run(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(TOOLS / "ingest_permits.py"), "--config", str(CONFIG),
             "--fixture", str(FIXTURE), "--dry-run", "--today", TODAY],
            capture_output=True, text=True, encoding="utf-8", cwd=str(ROOT))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("dry run, nothing written", proc.stdout)


if __name__ == "__main__":
    unittest.main()
