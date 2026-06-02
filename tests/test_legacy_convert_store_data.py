"""Regression tests for legacy DreamFinder JS/HTML formatting."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LEGACY_CONVERTER = ROOT / "tools" / "legacy" / "convert_store_data.py"


def _load_converter():
    """Load the legacy converter without requiring openpyxl in test envs."""
    old_openpyxl = sys.modules.get("openpyxl")
    sys.modules["openpyxl"] = types.SimpleNamespace()
    try:
        spec = importlib.util.spec_from_file_location("legacy_convert_store_data_for_test", LEGACY_CONVERTER)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module
    finally:
        if old_openpyxl is None:
            sys.modules.pop("openpyxl", None)
        else:
            sys.modules["openpyxl"] = old_openpyxl


class LegacyConverterEscapingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_converter()

    def test_js_value_escapes_script_breakout_chars(self) -> None:
        out = self.mod.js_value("</script><script>alert('x')</script>&")
        self.assertIn("\\u003c/script\\u003e", out)
        self.assertIn("\\u0026", out)
        self.assertNotIn("</script>", out)

    def test_format_mattress_js_uses_string_literals(self) -> None:
        out = self.mod.format_mattress_js({
            "id": "id'1",
            "name": "Name </script>",
            "brand": 'Brand "Quoted"',
            "subBrand": "Sub",
            "firmness": 5,
            "tags": ["cooling"],
            "features": ["soft"],
            "imageUrl": "https://example.invalid/a'b.webp",
            "reasons": {"default": "Don't break </script>"},
        })
        self.assertIn('"id\'1"', out)
        self.assertIn('Brand \\"Quoted\\"', out)
        self.assertNotIn("</script>", out)
        self.assertIn("\\u003c/script\\u003e", out)

    def test_format_accessory_js_escapes_description(self) -> None:
        out = self.mod.format_accessory_js({
            "id": "acc1",
            "name": "Accessory",
            "category": "Pillow",
            "price": 10,
            "image": "https://example.invalid/p.webp",
            "description": "O'Hara </script>",
            "subType": "Queen",
            "matchTags": ["soft"],
            "matchScores": {"default": 1},
        })
        self.assertIn('"O\'Hara \\u003c/script\\u003e"', out)
        self.assertNotIn("</script>", out)

    def test_footer_html_escapes_brand_fields(self) -> None:
        out = self.mod.generate_footer_html(
            {"footer_text": "Powered <b>bad</b>"},
            [{"name": 'Brand "One" <x>', "logoUrl": 'https://example.invalid/logo"bad.png'}],
            "https://example.invalid",
        )
        self.assertIn("Powered &lt;b&gt;bad&lt;/b&gt;", out)
        self.assertIn('alt="Brand &quot;One&quot; &lt;x&gt;"', out)
        self.assertIn("Brand &quot;One&quot; &lt;x&gt;", out)
        self.assertNotIn("<x>", out)


if __name__ == "__main__":
    unittest.main()
