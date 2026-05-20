"""Unit tests for tools/source_review.py. Stdlib unittest, no network."""

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
REAL_REGISTRY = ROOT / "sources" / "procurement_sources.json"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import source_review  # noqa: E402


def _synthetic_registry() -> list[dict]:
    """A small fixture exercising every cadence + has_api flag."""
    return [
        {
            "name": "FakeFed",
            "source_type": "federal_portal",
            "official_url": "https://fake.example.gov/",
            "has_api": True,
            "requires_login": False,
            "intake_method": "api",
            "geography": ["US"],
            "buyer_level": "federal",
            "search_terms": ["mattress"],
            "commodity_terms": ["mattress"],
            "cadence": "daily",
            "notes": "API-driven; should never appear in the review.",
        },
        {
            "name": "FakeStateWeekly",
            "source_type": "state_portal",
            "official_url": "https://state.example.gov/",
            "has_api": False,
            "requires_login": False,
            "intake_method": "saved_search",
            "geography": ["TX"],
            "buyer_level": "state",
            "search_terms": ["mattress", "dormitory"],
            "commodity_terms": ["mattress"],
            "cadence": "weekly",
            "notes": "weekly state portal",
        },
        {
            "name": "FakeCoopMonthly",
            "source_type": "cooperative",
            "official_url": "https://coop.example.org/",
            "has_api": False,
            "requires_login": True,
            "intake_method": "manual_review",
            "geography": ["US"],
            "buyer_level": "cooperative",
            "search_terms": ["mattress"],
            "commodity_terms": ["mattress"],
            "cadence": "monthly",
            "notes": "monthly cooperative",
        },
        {
            "name": "FakeVendorDbAdHoc",
            "source_type": "vendor_database",
            "official_url": "https://vdb.example.gov/",
            "has_api": False,
            "requires_login": True,
            "intake_method": "portal_registration",
            "geography": ["TX"],
            "buyer_level": "state",
            "search_terms": [],
            "commodity_terms": ["mattress"],
            "cadence": "ad_hoc",
            "notes": "ad_hoc vendor profile maintenance",
        },
    ]


class FilterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = _synthetic_registry()

    def test_filter_excludes_api_sources(self) -> None:
        # has_api=True must be excluded no matter what cadence is asked.
        for cadence in ("weekly", "monthly", "ad_hoc", "all"):
            out = source_review.filter_sources(self.sources, cadence)
            names = {s["name"] for s in out}
            self.assertNotIn("FakeFed", names, f"FakeFed leaked at cadence={cadence}")

    def test_filter_by_weekly(self) -> None:
        out = source_review.filter_sources(self.sources, "weekly")
        self.assertEqual([s["name"] for s in out], ["FakeStateWeekly"])

    def test_filter_by_monthly(self) -> None:
        out = source_review.filter_sources(self.sources, "monthly")
        self.assertEqual([s["name"] for s in out], ["FakeCoopMonthly"])

    def test_filter_by_ad_hoc(self) -> None:
        out = source_review.filter_sources(self.sources, "ad_hoc")
        self.assertEqual([s["name"] for s in out], ["FakeVendorDbAdHoc"])

    def test_filter_all_returns_non_api_in_registry_order(self) -> None:
        out = source_review.filter_sources(self.sources, "all")
        self.assertEqual(
            [s["name"] for s in out],
            ["FakeStateWeekly", "FakeCoopMonthly", "FakeVendorDbAdHoc"],
        )

    def test_list_cadences_excludes_api(self) -> None:
        # FakeFed has cadence=daily but has_api=True, so 'daily' must not appear.
        cadences = source_review.list_cadences(self.sources)
        self.assertEqual(cadences, ["ad_hoc", "monthly", "weekly"])

    def test_real_registry_excludes_sam_gov(self) -> None:
        # The committed registry should always exclude SAM.gov from review.
        with REAL_REGISTRY.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        for cadence in ("weekly", "monthly", "ad_hoc", "all"):
            out = source_review.filter_sources(data, cadence)
            names = {s["name"] for s in out}
            self.assertFalse(
                any("SAM.gov" in n for n in names),
                f"SAM.gov leaked at cadence={cadence}: {names}",
            )


class RenderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = _synthetic_registry()
        self.weekly = source_review.filter_sources(self.sources, "weekly")

    def test_render_includes_source_name_url_terms(self) -> None:
        out = source_review.render_checklist(self.weekly, "weekly", "2026-05-15")
        self.assertIn("FakeStateWeekly", out)
        self.assertIn("https://state.example.gov/", out)
        self.assertIn("mattress, dormitory", out)

    def test_render_includes_reminder_about_no_scraping(self) -> None:
        out = source_review.render_checklist(self.weekly, "weekly", "2026-05-15")
        self.assertIn("Do not scrape portals", out)
        self.assertIn("tools/pipeline.py add", out)

    def test_render_includes_date_and_cadence_in_title(self) -> None:
        out = source_review.render_checklist(self.weekly, "weekly", "2026-05-15")
        self.assertIn("# Portal review - 2026-05-15 (weekly cadence)", out)

    def test_render_includes_scoreboard_row_per_source(self) -> None:
        all_sources = source_review.filter_sources(self.sources, "all")
        out = source_review.render_checklist(all_sources, "all", "2026-05-15")
        # One scoreboard row per source (1, 2, 3 for the three non-API entries).
        for i, s in enumerate(all_sources, 1):
            self.assertIn(f"| {i} | {s['name']} |", out)

    def test_render_is_ascii_only_synthetic(self) -> None:
        out = source_review.render_checklist(self.weekly, "weekly", "2026-05-15")
        for idx, ch in enumerate(out):
            self.assertLess(
                ord(ch), 128,
                f"non-ASCII char at offset {idx}: {ch!r}",
            )

    def test_render_is_ascii_only_real_registry(self) -> None:
        # Real-registry regression: if any future entry slips a non-ASCII
        # char into name/url/notes, this test catches it before commit.
        with REAL_REGISTRY.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        all_sources = source_review.filter_sources(data, "all")
        out = source_review.render_checklist(all_sources, "all", "2026-05-15")
        for idx, ch in enumerate(out):
            self.assertLess(
                ord(ch), 128,
                f"non-ASCII char from real registry at offset {idx}: {ch!r}",
            )


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.registry = self.tmp / "registry.json"
        self.registry.write_text(json.dumps(_synthetic_registry()), encoding="utf-8")

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        rc = -1
        with redirect_stdout(out), redirect_stderr(err):
            try:
                rc = source_review.main(list(argv))
            except SystemExit as exc:
                rc = int(exc.code) if exc.code is not None else 0
        return rc, out.getvalue(), err.getvalue()

    def test_default_weekly_writes_file(self) -> None:
        output = self.tmp / "out.md"
        rc, stdout, err = self._run(
            "--registry", str(self.registry),
            "--output", str(output),
            "--date", "2026-05-15",
        )
        self.assertEqual(rc, 0, err)
        self.assertTrue(output.exists())
        body = output.read_text(encoding="utf-8")
        self.assertIn("FakeStateWeekly", body)
        self.assertNotIn("FakeCoopMonthly", body)
        self.assertNotIn("FakeFed", body)
        self.assertIn(f"wrote {output}", stdout)

    def test_dry_run_does_not_write(self) -> None:
        output = self.tmp / "out.md"
        rc, stdout, err = self._run(
            "--registry", str(self.registry),
            "--output", str(output),
            "--date", "2026-05-15",
            "--dry-run",
        )
        self.assertEqual(rc, 0, err)
        self.assertFalse(output.exists())
        # Stdout contains the rendered body.
        self.assertIn("FakeStateWeekly", stdout)

    def test_empty_result_exits_zero_no_file(self) -> None:
        # No source has cadence=daily AND has_api=False, so weekly+monthly+ad_hoc
        # all have content. Use a registry of API-only entries to force empty.
        api_only = [s for s in _synthetic_registry() if s["has_api"]]
        empty_registry = self.tmp / "api_only.json"
        empty_registry.write_text(json.dumps(api_only), encoding="utf-8")
        output = self.tmp / "should_not_exist.md"
        rc, stdout, _err = self._run(
            "--registry", str(empty_registry),
            "--output", str(output),
            "--cadence", "all",
            "--date", "2026-05-15",
        )
        self.assertEqual(rc, 0)
        self.assertFalse(output.exists())
        self.assertIn("nothing to review", stdout)

    def test_cadence_all_includes_every_non_api_source(self) -> None:
        output = self.tmp / "all.md"
        rc, _stdout, err = self._run(
            "--registry", str(self.registry),
            "--output", str(output),
            "--cadence", "all",
            "--date", "2026-05-15",
        )
        self.assertEqual(rc, 0, err)
        body = output.read_text(encoding="utf-8")
        self.assertIn("FakeStateWeekly", body)
        self.assertIn("FakeCoopMonthly", body)
        self.assertIn("FakeVendorDbAdHoc", body)
        self.assertNotIn("FakeFed", body)

    def test_list_cadences_prints_and_exits(self) -> None:
        output = self.tmp / "should_not_exist.md"
        rc, stdout, err = self._run(
            "--registry", str(self.registry),
            "--output", str(output),
            "--list-cadences",
        )
        self.assertEqual(rc, 0, err)
        self.assertFalse(output.exists())
        # Expect the three non-API cadences in sorted order, one per line.
        self.assertEqual(stdout.strip().splitlines(), ["ad_hoc", "monthly", "weekly"])

    def test_invalid_date_rejected(self) -> None:
        rc, _out, err = self._run(
            "--registry", str(self.registry),
            "--date", "yesterday",
        )
        self.assertEqual(rc, 2)
        self.assertIn("YYYY-MM-DD", err)

    def test_missing_registry_errors(self) -> None:
        missing = self.tmp / "does_not_exist.json"
        rc, _out, err = self._run("--registry", str(missing))
        self.assertEqual(rc, 1)
        self.assertIn("does_not_exist.json", err)

    def test_real_registry_smoke_weekly(self) -> None:
        # End-to-end: real registry, weekly cadence, custom output path.
        output = self.tmp / "real_weekly.md"
        rc, _out, err = self._run(
            "--registry", str(REAL_REGISTRY),
            "--output", str(output),
            "--cadence", "weekly",
            "--date", "2026-05-15",
        )
        self.assertEqual(rc, 0, err)
        body = output.read_text(encoding="utf-8")
        # Real weekly portals per the committed registry.
        for expected in (
            "Texas ESBD / Texas SmartBuy",
            "City of Houston Beacon Bid",
            "Harris County Bonfire",
            "Houston ISD IonWave",
        ):
            self.assertIn(expected, body)
        self.assertNotIn("SAM.gov", body)


class RegistryDataShapeTests(unittest.TestCase):
    """Assertions over the committed source registry's data shape."""

    def setUp(self) -> None:
        with REAL_REGISTRY.open(encoding="utf-8") as fh:
            self.entries = json.load(fh)

    def _by_name(self, name: str) -> dict:
        for entry in self.entries:
            if entry.get("name") == name:
                return entry
        raise AssertionError(f"registry missing entry named {name!r}")

    def test_csv_export_supported_is_bool_when_present(self) -> None:
        # Field is intentionally absent on entries that have not been
        # walked. When present, it MUST be a Python bool - a string
        # "true"/"false" or null would silently break flag-driven routing.
        for entry in self.entries:
            if "csv_export_supported" in entry:
                self.assertIsInstance(
                    entry["csv_export_supported"],
                    bool,
                    f"{entry.get('name')!r}: csv_export_supported must be bool, "
                    f"got {type(entry['csv_export_supported']).__name__}",
                )

    def test_walked_weekly_portals_have_expected_csv_export_values(self) -> None:
        # Codifies the operator's documented walk findings so silent
        # drift (entry removal, value flip, name rename) fails loudly.
        expected = {
            "Texas ESBD / Texas SmartBuy": True,
            "City of Houston Beacon Bid": False,
            "Harris County Bonfire": False,
            "Houston ISD IonWave": False,
        }
        for name, want in expected.items():
            entry = self._by_name(name)
            self.assertIn(
                "csv_export_supported", entry,
                f"{name!r}: csv_export_supported missing",
            )
            self.assertEqual(
                entry["csv_export_supported"], want,
                f"{name!r}: csv_export_supported={entry['csv_export_supported']!r}, "
                f"expected {want!r}",
            )


if __name__ == "__main__":
    unittest.main()
