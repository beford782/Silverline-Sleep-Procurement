#!/usr/bin/env python3
"""
portal_csv_mapping.py - inspect portal CSV headers and draft a mapping.

This helper does not ingest opportunities. It reads the header row from
an operator-downloaded portal CSV, suggests mappings to the canonical
pipeline fields used by tools/ingest_portal_csv.py, and can write a
starter JSON config under configs/portal_csv/.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "configs" / "portal_csv"
DEFAULT_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d"]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest_portal_csv import MAPPABLE_FIELDS, load_mapping  # noqa: E402
from pipeline import slugify  # noqa: E402


SYNONYMS: dict[str, tuple[str, ...]] = {
    "solicitation_number": (
        "solicitation",
        "solicitation number",
        "solicitation #",
        "bid number",
        "bid #",
        "event number",
        "event id",
        "rfp number",
        "ifb number",
        "reference number",
    ),
    "title": (
        "title",
        "description",
        "opportunity title",
        "solicitation title",
        "event title",
        "project title",
    ),
    "buyer": (
        "buyer",
        "agency",
        "department",
        "organization",
        "issuing agency",
        "owner",
        "entity",
    ),
    "portal_url": (
        "url",
        "link",
        "solicitation url",
        "posting url",
        "opportunity url",
        "view",
    ),
    "posted_date": (
        "posted date",
        "publish date",
        "publication date",
        "issued date",
        "open date",
        "release date",
    ),
    "due_date": (
        "due date",
        "closing date",
        "close date",
        "response due",
        "response deadline",
        "bid due date",
        "submission deadline",
    ),
    "question_deadline": (
        "question deadline",
        "questions due",
        "qa deadline",
        "q&a deadline",
        "inquiry deadline",
        "clarification deadline",
    ),
    "delivery_location": (
        "delivery location",
        "location",
        "place of performance",
        "ship to",
        "shipping location",
        "county",
        "city",
    ),
    "commodity_terms": (
        "commodity",
        "commodity code",
        "nigp",
        "nigp code",
        "class/item",
        "category",
        "classification",
    ),
    "estimated_value": (
        "estimated value",
        "estimated amount",
        "budget",
        "value",
        "amount",
    ),
    "primary_products": (
        "products",
        "items",
        "scope",
        "goods",
        "category description",
    ),
    "notes": (
        "notes",
        "notice type",
        "type",
        "status",
        "comments",
    ),
}


def normalize_header(value: str) -> str:
    """Normalize a CSV header for conservative matching."""
    normalized = re.sub(r"[^a-z0-9]+", " ", (value or "").strip().lower())
    return re.sub(r"\s+", " ", normalized).strip()


def read_headers(csv_path: Path, encoding: str = "utf-8-sig") -> list[str]:
    with csv_path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.reader(fh)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{csv_path}: CSV is empty") from exc
    return [h.strip() for h in headers]


def suggest_columns(headers: list[str]) -> dict[str, str]:
    """Return {canonical_field: csv_header} using exact normalized matches."""
    normalized_to_header: dict[str, str] = {}
    for header in headers:
        normalized = normalize_header(header)
        if normalized and normalized not in normalized_to_header:
            normalized_to_header[normalized] = header

    suggestions: dict[str, str] = {}
    used_headers: set[str] = set()
    for field in MAPPABLE_FIELDS:
        candidates = (field.replace("_", " "), *SYNONYMS.get(field, ()))
        for candidate in candidates:
            normalized = normalize_header(candidate)
            header = normalized_to_header.get(normalized)
            if header and header not in used_headers:
                suggestions[field] = header
                used_headers.add(header)
                break
    return suggestions


def build_mapping(source: str, headers: list[str], date_formats: list[str]) -> dict:
    return {
        "source": source,
        "columns": suggest_columns(headers),
        "date_formats": date_formats,
    }


def render_report(headers: list[str], mapping: dict) -> str:
    lines: list[str] = []
    lines.append("CSV headers")
    lines.append("-----------")
    for i, header in enumerate(headers, 1):
        lines.append(f"{i}. {header}")
    lines.append("")
    lines.append("Suggested mapping")
    lines.append("-----------------")
    columns = mapping.get("columns") or {}
    if columns:
        for field in MAPPABLE_FIELDS:
            if field in columns:
                lines.append(f"{field}: {columns[field]}")
    else:
        lines.append("(none)")
    lines.append("")
    unmapped = [h for h in headers if h not in set(columns.values())]
    lines.append("Unmapped CSV headers")
    lines.append("--------------------")
    if unmapped:
        for header in unmapped:
            lines.append(f"- {header}")
    else:
        lines.append("(none)")
    return "\n".join(lines) + "\n"


def _date_formats(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv_path", help="Portal CSV export to inspect.")
    parser.add_argument("--source", required=True, help="Source label to place in the generated mapping.")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding (default: %(default)s)")
    parser.add_argument(
        "--date-formats",
        type=_date_formats,
        default=list(DEFAULT_DATE_FORMATS),
        help="Comma-separated strptime formats for mapped date fields.",
    )
    parser.add_argument("--output", default=None, help="Mapping JSON output path.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Output directory if --output is omitted.")
    parser.add_argument("--write", action="store_true", help="Write the mapping JSON after printing the report.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing mapping file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"error: csv_path not found: {csv_path}", file=sys.stderr)
        return 2
    try:
        headers = read_headers(csv_path, args.encoding)
    except UnicodeDecodeError as exc:
        print(f"error: cannot decode {csv_path} as {args.encoding}: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    mapping = build_mapping(args.source, headers, list(args.date_formats))
    sys.stdout.write(render_report(headers, mapping))

    if not args.write:
        print("(preview only; pass --write to save a mapping JSON)")
        return 0

    out_path = Path(args.output) if args.output else Path(args.output_dir) / f"{slugify(args.source).replace('-', '_')}.json"
    if out_path.exists() and not args.force:
        print(f"error: {out_path} already exists. Pass --force to overwrite.", file=sys.stderr)
        return 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    try:
        load_mapping(out_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: wrote invalid mapping {out_path}: {exc}", file=sys.stderr)
        return 1
    print(f"wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
