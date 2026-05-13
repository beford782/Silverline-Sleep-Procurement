"""Unit tests for the procurement toolkit. Stdlib unittest, no fixtures."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

# Make sibling tools/ importable regardless of how pytest/unittest is invoked.
ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import generate_procurement_packet as gpp  # noqa: E402
import validate_vendor_profile as vvp  # noqa: E402


SAMPLE_CSV = textwrap.dedent(
    """\
    Section,Question / Field,Your Answer,Guidance / Examples
    Company Profile,Company legal name,Acme Mattress Co,Legal entity used for government bids.
    Company Profile,DBA / brand name,,If different from legal name.
    Company Profile,Hostile <script>,"Foo & Bar | Baz","Pipe | and < > & chars"
    Products,Dormitory mattresses,Yes,Twin XL etc.
    Products,Bed frames,,Platform; metal.
    """
)


class CsvParsingTests(unittest.TestCase):
    def test_groups_by_section_and_preserves_order(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            fh.write(SAMPLE_CSV)
            path = fh.name
        try:
            sections = gpp.read_questionnaire(path)
        finally:
            os.unlink(path)

        self.assertEqual(list(sections.keys()), ["Company Profile", "Products"])
        self.assertEqual(len(sections["Company Profile"]), 3)
        self.assertEqual(sections["Company Profile"][0]["answer"], "Acme Mattress Co")
        self.assertEqual(sections["Company Profile"][1]["answer"], "")

    def test_answered_only_drops_blank_rows_and_empty_sections(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            # Section 'Empty' has only blank answers and should disappear.
            fh.write(SAMPLE_CSV + "Empty,Nothing,,placeholder\n")
            path = fh.name
        try:
            sections = gpp.read_questionnaire(path, answered_only=True)
        finally:
            os.unlink(path)

        self.assertEqual(list(sections.keys()), ["Company Profile", "Products"])
        # Every retained row has a non-blank answer.
        for rows in sections.values():
            for row in rows:
                self.assertTrue(row["answer"])

    def test_missing_columns_exits(self) -> None:
        bad = "Section,Question / Field\nA,B\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            fh.write(bad)
            path = fh.name
        try:
            with self.assertRaises(SystemExit) as cm:
                gpp.read_questionnaire(path)
            self.assertIn("missing expected columns", str(cm.exception))
        finally:
            os.unlink(path)


class RenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write(SAMPLE_CSV)
        tmp.close()
        self.path = tmp.name
        self.addCleanup(os.unlink, self.path)
        self.sections = gpp.read_questionnaire(self.path)

    def test_markdown_pipes_in_answer_are_escaped(self) -> None:
        md = gpp.render_markdown("Acme", self.sections, "2026-05-13")
        # The hostile cell contains a literal pipe; it should be escaped so
        # the markdown table parser doesn't split the cell.
        self.assertIn("Foo & Bar \\| Baz", md)

    def test_html_escapes_special_characters(self) -> None:
        html_out = gpp.render_html("Acme", self.sections, "2026-05-13")
        self.assertNotIn("<script>", html_out)
        self.assertIn("&lt;script&gt;", html_out)
        self.assertIn("Foo &amp; Bar | Baz", html_out)
        self.assertIn("<!DOCTYPE html>", html_out)
        # No external assets / no JS.
        self.assertNotIn("<script", html_out)
        self.assertNotIn("http://", html_out)

    def test_generated_date_is_used_verbatim_in_both_renders(self) -> None:
        md = gpp.render_markdown("Acme", self.sections, "1999-12-31")
        html_out = gpp.render_html("Acme", self.sections, "1999-12-31")
        self.assertIn("Generated 1999-12-31", md)
        self.assertIn("Generated 1999-12-31", html_out)

    def test_rendering_is_deterministic(self) -> None:
        first = gpp.render_markdown("Acme", self.sections, "2026-05-13")
        second = gpp.render_markdown("Acme", self.sections, "2026-05-13")
        self.assertEqual(first, second)


class GeneratorCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(self._cleanup_tmpdir)
        self.csv_path = os.path.join(self.tmpdir, "in.csv")
        with open(self.csv_path, "w", encoding="utf-8") as fh:
            fh.write(SAMPLE_CSV)

    def _cleanup_tmpdir(self) -> None:
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, *argv: str) -> int:
        buf_out, buf_err = io.StringIO(), io.StringIO()
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            return gpp.main(list(argv))

    def test_output_stem_overrides_filename(self) -> None:
        out = os.path.join(self.tmpdir, "out")
        rc = self._run(
            self.csv_path,
            "--vendor", "Acme",
            "--output-dir", out,
            "--output-stem", "custom-name",
            "--generated-date", "2026-05-13",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "custom-name.md")))
        self.assertTrue(os.path.isfile(os.path.join(out, "custom-name.html")))

    def test_slug_alias_still_works(self) -> None:
        out = os.path.join(self.tmpdir, "out2")
        rc = self._run(
            self.csv_path,
            "--vendor", "Acme",
            "--out-dir", out,
            "--slug", "via-alias",
            "--generated-date", "2026-05-13",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(out, "via-alias.md")))

    def test_default_output_dir_is_build_generated(self) -> None:
        # We can't write into the real CWD safely; chdir into tmp.
        cwd = os.getcwd()
        os.chdir(self.tmpdir)
        try:
            rc = self._run(
                self.csv_path,
                "--vendor", "Acme",
                "--generated-date", "2026-05-13",
            )
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(os.path.join("build", "generated", "acme.md")))
        finally:
            os.chdir(cwd)

    def test_bad_generated_date_rejected(self) -> None:
        out = os.path.join(self.tmpdir, "out3")
        with self.assertRaises(SystemExit):
            self._run(
                self.csv_path,
                "--vendor", "Acme",
                "--output-dir", out,
                "--generated-date", "yesterday",
            )

    def test_missing_csv_returns_nonzero(self) -> None:
        rc = self._run(
            os.path.join(self.tmpdir, "missing.csv"),
            "--vendor", "Acme",
            "--generated-date", "2026-05-13",
            "--output-dir", self.tmpdir,
        )
        self.assertEqual(rc, 1)


VALID_PROFILE = {
    "vendor": {"legal_name": "Acme"},
    "company": {"delivery_method": "own_fleet"},
    "products": {"dorm_mattress": "yes"},
    "compliance": {"insurance": ["general_liability"]},
    "target_buyers": {"highest": ["cities"]},
    "portal_status": [
        {"portal": "Texas CMBL", "status": "registered", "next_step": "audit codes"}
    ],
}


class ValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(vvp.SCHEMA_PATH_DEFAULT, "r", encoding="utf-8") as fh:
            cls.schema = json.load(fh)

    def test_committed_profile_validates(self) -> None:
        profile_path = ROOT / "vendor-profiles" / "continental_silverline.profile.json"
        with open(profile_path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertEqual(vvp.validate(doc, self.schema), [])

    def test_missing_required_top_level_property_reported(self) -> None:
        doc = dict(VALID_PROFILE)
        del doc["products"]
        errors = vvp.validate(doc, self.schema)
        self.assertTrue(any("missing required property 'products'" in e for e in errors))

    def test_unknown_enum_reported(self) -> None:
        doc = json.loads(json.dumps(VALID_PROFILE))
        doc["company"]["delivery_method"] = "bogus"
        errors = vvp.validate(doc, self.schema)
        self.assertTrue(any("not in enum" in e for e in errors))

    def test_unexpected_property_reported(self) -> None:
        doc = json.loads(json.dumps(VALID_PROFILE))
        doc["portal_status"][0]["surprise"] = 1
        errors = vvp.validate(doc, self.schema)
        self.assertTrue(any("unexpected property 'surprise'" in e for e in errors))

    def test_min_length_violation_reported(self) -> None:
        doc = json.loads(json.dumps(VALID_PROFILE))
        doc["vendor"]["legal_name"] = ""
        errors = vvp.validate(doc, self.schema)
        self.assertTrue(any("shorter than minLength" in e for e in errors))

    def test_type_mismatch_reported(self) -> None:
        doc = json.loads(json.dumps(VALID_PROFILE))
        doc["portal_status"] = "not a list"
        errors = vvp.validate(doc, self.schema)
        self.assertTrue(any("expected array" in e for e in errors))

    def test_cli_exit_codes(self) -> None:
        ok = vvp.main([str(ROOT / "vendor-profiles" / "continental_silverline.profile.json")])
        self.assertEqual(ok, 0)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump({"vendor": {"legal_name": ""}}, fh)
            bad_path = fh.name
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = vvp.main([bad_path])
            self.assertEqual(rc, 1)
            self.assertIn("FAIL", buf.getvalue())
        finally:
            os.unlink(bad_path)


if __name__ == "__main__":
    unittest.main()
