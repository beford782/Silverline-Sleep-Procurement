#!/usr/bin/env python3
"""
generate_procurement_packet.py

Reads a filled-in mattress procurement questionnaire CSV (see
templates/mattress_bid_setup_questionnaire.csv) and emits:

  * <stem>.md   — section-grouped markdown procurement packet
  * <stem>.html — standalone printable HTML (inline CSS, no JS)

The script uses only the Python standard library so the repo stays
lightweight and cross-platform.

Usage:
    python tools/generate_procurement_packet.py INPUT.csv \
        --vendor "Continental Silverline" \
        --output-dir build/generated/ \
        --generated-date 2026-05-13

Notable flags:
    --output-dir DIR       Where to write output (default: build/generated)
    --output-stem STEM     Filename stem (default: slug of vendor name)
    --generated-date DATE  ISO date stamped on the packet (default: today).
                           Pin for deterministic example output.
    --answered-only        Drop rows whose Your Answer is blank.
    --vendor NAME          Vendor name used in titles and filenames.

`--slug` is accepted as a backwards-compatible alias for --output-stem,
and `--out-dir` for --output-dir.
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import re
import sys
from collections import OrderedDict
from datetime import date, datetime


EXPECTED_COLUMNS = ("Section", "Question / Field", "Your Answer", "Guidance / Examples")
DEFAULT_OUTPUT_DIR = os.path.join("build", "generated")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "vendor"


def _parse_iso_date(value: str) -> str:
    """Accept YYYY-MM-DD; raise argparse.ArgumentTypeError on anything else."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--generated-date must be YYYY-MM-DD ({exc})"
        ) from exc


def read_questionnaire(path: str, answered_only: bool = False) -> "OrderedDict[str, list[dict]]":
    """Return rows grouped by Section, preserving CSV order.

    If answered_only is set, rows whose Your Answer cell is blank are
    skipped, and sections that end up empty are dropped.
    """
    sections: "OrderedDict[str, list[dict]]" = OrderedDict()
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in EXPECTED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"CSV is missing expected columns: {missing}. Found: {reader.fieldnames}"
            )
        for row in reader:
            answer = (row.get("Your Answer") or "").strip()
            if answered_only and not answer:
                continue
            section = (row.get("Section") or "").strip() or "General"
            sections.setdefault(section, []).append(
                {
                    "field": (row.get("Question / Field") or "").strip(),
                    "answer": answer,
                    "guidance": (row.get("Guidance / Examples") or "").strip(),
                }
            )
    return sections


def _counts(sections: "OrderedDict[str, list[dict]]") -> tuple[int, int]:
    answered = sum(1 for rows in sections.values() for r in rows if r["answer"])
    total = sum(len(rows) for rows in sections.values())
    return answered, total


def render_markdown(
    vendor: str,
    sections: "OrderedDict[str, list[dict]]",
    generated_date: str,
) -> str:
    answered, total = _counts(sections)

    lines: list[str] = []
    lines.append(f"# {vendor} — Procurement Packet")
    lines.append("")
    lines.append(f"_Generated {generated_date} · {answered} of {total} fields answered._")
    lines.append("")
    lines.append("> Built from the mattress bid setup questionnaire. Blank rows are")
    lines.append("> intentionally preserved so reviewers can see what is still")
    lines.append("> outstanding.")
    lines.append("")

    for section, rows in sections.items():
        lines.append(f"## {section}")
        lines.append("")
        lines.append("| Field | Answer | Guidance |")
        lines.append("| --- | --- | --- |")
        for r in rows:
            field = _md_cell(r["field"])
            answer = _md_cell(r["answer"]) if r["answer"] else "_—_"
            guidance = _md_cell(r["guidance"])
            lines.append(f"| {field} | {answer} | {guidance} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _md_cell(text: str) -> str:
    if not text:
        return ""
    return text.replace("|", "\\|").replace("\n", " ")


HTML_CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               "Helvetica Neue", Arial, sans-serif;
  font-size: 11pt;
  color: #1a1a1a;
  line-height: 1.45;
  margin: 1.5rem auto;
  max-width: 8.5in;
  padding: 0 1rem;
}
h1 {
  font-size: 1.8rem;
  border-bottom: 3px solid #1f3a5c;
  padding-bottom: 0.3rem;
  margin-top: 0;
}
h2 {
  font-size: 1.15rem;
  color: #1f3a5c;
  margin-top: 1.6rem;
  margin-bottom: 0.4rem;
  border-bottom: 1px solid #d0d4dc;
  padding-bottom: 0.15rem;
}
.meta { color: #555; font-size: 0.92rem; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 0.4rem 0 1rem 0;
  font-size: 10pt;
  table-layout: fixed;
}
th, td {
  border: 1px solid #ccd1d9;
  padding: 0.4rem 0.55rem;
  vertical-align: top;
  text-align: left;
  word-wrap: break-word;
}
th {
  background: #1f3a5c;
  color: #fff;
  font-weight: 600;
}
tr:nth-child(even) td { background: #f7f8fa; }
td.empty { color: #999; font-style: italic; }
col.field    { width: 28%; }
col.answer   { width: 42%; }
col.guidance { width: 30%; }
@media print {
  body { margin: 0; max-width: none; padding: 0; }
  h2 { page-break-after: avoid; }
  table { page-break-inside: avoid; }
}
"""


def render_html(
    vendor: str,
    sections: "OrderedDict[str, list[dict]]",
    generated_date: str,
) -> str:
    answered, total = _counts(sections)

    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en">')
    parts.append("<head>")
    parts.append('<meta charset="utf-8" />')
    parts.append(f"<title>{html.escape(vendor)} — Procurement Packet</title>")
    parts.append(f"<style>{HTML_CSS}</style>")
    parts.append("</head>")
    parts.append("<body>")
    parts.append(f"<h1>{html.escape(vendor)} — Procurement Packet</h1>")
    parts.append(
        f'<p class="meta">Generated {html.escape(generated_date)} &middot; '
        f"{answered} of {total} fields answered.</p>"
    )

    for section, rows in sections.items():
        parts.append(f"<h2>{html.escape(section)}</h2>")
        parts.append("<table>")
        parts.append('<colgroup><col class="field"><col class="answer"><col class="guidance"></colgroup>')
        parts.append("<thead><tr><th>Field</th><th>Answer</th><th>Guidance</th></tr></thead>")
        parts.append("<tbody>")
        for r in rows:
            field = html.escape(r["field"])
            guidance = html.escape(r["guidance"])
            if r["answer"]:
                answer_cell = f"<td>{html.escape(r['answer'])}</td>"
            else:
                answer_cell = '<td class="empty">—</td>'
            parts.append(f"<tr><td>{field}</td>{answer_cell}<td>{guidance}</td></tr>")
        parts.append("</tbody></table>")

    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("csv_path", help="Path to a filled-in questionnaire CSV")
    parser.add_argument("--vendor", default=None, help="Vendor name (titles and filenames)")
    parser.add_argument(
        "--output-dir", "--out-dir",
        dest="output_dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--output-stem", "--slug",
        dest="output_stem",
        default=None,
        help="Filename stem (default: slug of vendor name)",
    )
    parser.add_argument(
        "--generated-date",
        type=_parse_iso_date,
        default=None,
        help="ISO date stamped on the packet (default: today). Pin for determinism.",
    )
    parser.add_argument(
        "--answered-only",
        action="store_true",
        help="Drop questionnaire rows whose Your Answer cell is blank.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if not os.path.isfile(args.csv_path):
        print(f"error: {args.csv_path} not found", file=sys.stderr)
        return 1

    sections = read_questionnaire(args.csv_path, answered_only=args.answered_only)
    if not sections:
        print("error: no rows to render (all answers blank with --answered-only?)", file=sys.stderr)
        return 1

    vendor = args.vendor or os.path.splitext(os.path.basename(args.csv_path))[0].replace("_", " ").title()
    stem = args.output_stem or slugify(vendor)
    generated_date = args.generated_date or date.today().isoformat()

    os.makedirs(args.output_dir, exist_ok=True)
    md_path = os.path.join(args.output_dir, f"{stem}.md")
    html_path = os.path.join(args.output_dir, f"{stem}.html")

    with open(md_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_markdown(vendor, sections, generated_date))
    with open(html_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(render_html(vendor, sections, generated_date))

    answered, total = _counts(sections)
    print(f"Vendor:   {vendor}")
    print(f"Sections: {len(sections)}")
    print(f"Answered: {answered}/{total}")
    print(f"Date:     {generated_date}")
    print(f"Wrote:    {md_path}")
    print(f"Wrote:    {html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
