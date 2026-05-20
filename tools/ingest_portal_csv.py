#!/usr/bin/env python3
"""
ingest_portal_csv.py - ingest an operator-downloaded portal CSV into the
active pipeline.

The operator downloads a CSV export from a procurement portal (e.g. Texas
ESBD) and runs this script with a column-mapping config. The script does
NOT log in to or scrape the portal. New portals are added by writing a
new mapping JSON in configs/portal_csv/, not by changing code.

Stdlib only. No third-party dependencies.

Usage:
    python tools/ingest_portal_csv.py path/to/export.csv \\
        --mapping configs/portal_csv/esbd.json \\
        [--source "Texas ESBD"] \\
        [--<field>-column "Real Header Name" ...] \\
        [--encoding utf-8-sig] \\
        [--dry-run] \\
        [--active PATH] [--archive PATH]

Mapping config shape:
    {
      "source": "Texas ESBD",
      "columns": {"<canonical_field>": "<csv header>", ...},
      "date_formats": ["%m/%d/%Y", ...]   # optional, additive to ISO fallback
    }

Precedence per field: CLI per-column flag > mapping file > unmapped (empty).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"

# Reuse pipeline helpers; do not duplicate canonical schema or id rules.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import (  # noqa: E402
    CANONICAL_HEADER,
    derive_opportunity_id,
    read_rows,
    write_rows_atomic,
)


# Subset of CANONICAL_HEADER that a portal CSV is allowed to populate.
# The rest are derived (opportunity_id, source, status, ...) or operator-
# filled later (fit_score, risk_level, owner).
MAPPABLE_FIELDS = (
    "solicitation_number",
    "title",
    "buyer",
    "portal_url",
    "posted_date",
    "due_date",
    "question_deadline",
    "delivery_location",
    "commodity_terms",
    "estimated_value",
    "primary_products",
    "notes",
)

DATE_FIELDS = ("posted_date", "due_date", "question_deadline")

ALLOWED_MAPPING_KEYS = {"source", "columns", "date_formats"}

DEFAULT_NEXT_ACTION = "Triage: read solicitation, run pipeline.py score, decide bid/no-bid"


def load_mapping(path: Path) -> dict:
    """Read and validate a mapping JSON.

    Unknown top-level keys and unknown canonical field names raise
    ValueError so typos surface immediately rather than silently dropping
    data into empty pipeline columns.
    """
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: mapping must be a JSON object")

    unknown_top = set(data.keys()) - ALLOWED_MAPPING_KEYS
    if unknown_top:
        raise ValueError(
            f"{path}: unknown top-level key(s) {sorted(unknown_top)}; "
            f"allowed: {sorted(ALLOWED_MAPPING_KEYS)}"
        )

    columns = data.get("columns") or {}
    if not isinstance(columns, dict):
        raise ValueError(f"{path}: 'columns' must be a JSON object")
    unknown_cols = set(columns.keys()) - set(MAPPABLE_FIELDS)
    if unknown_cols:
        raise ValueError(
            f"{path}: unknown canonical field(s) in columns: {sorted(unknown_cols)}; "
            f"mappable: {sorted(MAPPABLE_FIELDS)}"
        )

    date_formats = data.get("date_formats") or []
    if not isinstance(date_formats, list) or not all(isinstance(f, str) for f in date_formats):
        raise ValueError(f"{path}: 'date_formats' must be a list of strptime format strings")

    return data


def resolve_source(mapping: dict, cli_source: str | None) -> str:
    """CLI --source wins over mapping 'source'; missing both is fatal."""
    if cli_source:
        return cli_source
    src = mapping.get("source")
    if not src:
        raise ValueError("'source' missing from mapping and no --source override")
    return str(src)


def resolve_columns(mapping: dict, cli_overrides: dict[str, str | None]) -> dict[str, str]:
    """Final {canonical_field: csv_header} after precedence.

    Precedence: CLI per-column flag > mapping file > unmapped (omitted).
    """
    base = dict(mapping.get("columns") or {})
    out: dict[str, str] = {}
    for field in MAPPABLE_FIELDS:
        cli_val = cli_overrides.get(field)
        if cli_val:
            out[field] = cli_val
        elif field in base and base[field]:
            out[field] = base[field]
    return out


def normalize_date(value: str, formats: list[str], bad_values: list[str]) -> str:
    """Return YYYY-MM-DD or empty. Record the raw value in bad_values on failure.

    Tries each strptime format in order, then datetime.fromisoformat as a
    final fallback. On total failure, appends the raw value to bad_values
    and returns empty string - safer than a first-10-chars slice, which
    would poison pipeline.py's strict YYYY-MM-DD validation.
    """
    v = (value or "").strip()
    if not v:
        return ""
    for fmt in formats:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(v).date().isoformat()
    except ValueError:
        bad_values.append(v)
        return ""


def clean_estimated_value(value: str) -> str:
    """Lenient: strip $ and , and whitespace. No numeric validation."""
    if not value:
        return ""
    return value.replace("$", "").replace(",", "").strip()


def csv_row_to_pipeline_row(
    csv_row: dict,
    columns: dict[str, str],
    source: str,
    date_formats: list[str],
    today: str,
    bad_dates: list[str],
) -> dict:
    """Map one CSV row dict onto a canonical pipeline row dict."""
    row = {k: "" for k in CANONICAL_HEADER}

    raw: dict[str, str] = {
        field: (csv_row.get(header) or "").strip()
        for field, header in columns.items()
    }

    for field in DATE_FIELDS:
        if field in raw:
            raw[field] = normalize_date(raw[field], date_formats, bad_dates)

    if "estimated_value" in raw:
        raw["estimated_value"] = clean_estimated_value(raw["estimated_value"])

    for field, value in raw.items():
        row[field] = value

    # Use pipeline.derive_opportunity_id rather than duplicating the slug
    # logic locally. ingest_sam.py builds the id inline with a 120-char
    # cap, but the shared helper is the long-term canonical form - if id
    # length becomes a problem, we tighten derive_opportunity_id once for
    # all ingesters instead of drifting per-portal.
    row["opportunity_id"] = derive_opportunity_id(
        source,
        row["buyer"],
        row["solicitation_number"],
        row["title"],
    )
    row["source"] = source
    row["status"] = "watching"
    row["next_action"] = DEFAULT_NEXT_ACTION
    row["created_date"] = today
    row["last_reviewed"] = today
    return row


def _ids_and_sols(rows: list[dict]) -> tuple[set[str], set[str]]:
    ids = {(r.get("opportunity_id") or "").strip() for r in rows if r.get("opportunity_id")}
    sols = {(r.get("solicitation_number") or "").strip() for r in rows if r.get("solicitation_number")}
    return ids, sols


def ingest(
    csv_rows: Iterable[dict],
    columns: dict[str, str],
    source: str,
    date_formats: list[str],
    existing_active: list[dict],
    existing_archive: list[dict],
    today: str,
) -> tuple[list[dict], int, int, list[str]]:
    """Partition incoming CSV rows into pipeline rows and dupe counts.

    Returns (new_rows, n_active_dupes, n_archive_dupes, bad_dates).

    Dupe attribution: an archive match wins over an active match. The
    operator's most important signal is "previously closed, do not
    re-open." Intra-batch duplicates (same id/sol seen twice in the
    incoming CSV) are counted as active dupes since the first occurrence
    is already queued for the active pipeline.
    """
    active_ids, active_sols = _ids_and_sols(existing_active)
    archive_ids, archive_sols = _ids_and_sols(existing_archive)

    new_rows: list[dict] = []
    n_active = 0
    n_archive = 0
    bad_dates: list[str] = []

    seen_ids: set[str] = set()
    seen_sols: set[str] = set()

    for csv_row in csv_rows:
        row = csv_row_to_pipeline_row(csv_row, columns, source, date_formats, today, bad_dates)
        oid = row["opportunity_id"]
        sol = row["solicitation_number"]

        in_archive = oid in archive_ids or (sol and sol in archive_sols)
        if in_archive:
            n_archive += 1
            continue

        in_active = oid in active_ids or (sol and sol in active_sols)
        in_seen = oid in seen_ids or (sol and sol in seen_sols)
        if in_active or in_seen:
            n_active += 1
            continue

        seen_ids.add(oid)
        if sol:
            seen_sols.add(sol)
        new_rows.append(row)

    return new_rows, n_active, n_archive, bad_dates


def _read_existing_or_empty(path: Path) -> list[dict]:
    if not path.exists():
        return []
    _, rows = read_rows(path)
    return rows


def _validate_csv_headers(fieldnames: list[str], columns: dict[str, str], csv_path: Path) -> None:
    missing = [(field, header) for field, header in columns.items() if header not in fieldnames]
    if missing:
        details = ", ".join(f"'{h}' (for field '{f}')" for f, h in missing)
        raise ValueError(
            f"mapped header(s) not found in {csv_path}: {details}. CSV headers are: {fieldnames}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("csv_path", help="Path to a portal CSV export (operator-downloaded).")
    parser.add_argument(
        "--mapping",
        required=True,
        help="Path to a JSON column-mapping config (e.g. configs/portal_csv/esbd.json).",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Override the 'source' value from the mapping config.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="CSV file encoding (default: utf-8-sig, transparently handles UTF-8 BOM).",
    )
    for field in MAPPABLE_FIELDS:
        parser.add_argument(
            f"--{field.replace('_', '-')}-column",
            dest=f"col_{field}",
            default=None,
            help=f"Override the mapping file's '{field}' column header.",
        )
    parser.add_argument(
        "--active",
        default=str(DEFAULT_ACTIVE),
        help=f"Active pipeline CSV write target (default: {DEFAULT_ACTIVE.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--archive",
        default=str(DEFAULT_ARCHIVE),
        help=(
            f"Archive pipeline CSV consulted for dedup only; never written. "
            f"Default: {DEFAULT_ARCHIVE.relative_to(REPO_ROOT)}."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; do not write.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    csv_path = Path(args.csv_path)
    mapping_path = Path(args.mapping)
    active_path = Path(args.active)
    archive_path = Path(args.archive)

    if not csv_path.exists():
        print(f"error: csv_path not found: {csv_path}", file=sys.stderr)
        return 2
    if not mapping_path.exists():
        print(f"error: mapping not found: {mapping_path}", file=sys.stderr)
        return 2

    try:
        mapping = load_mapping(mapping_path)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        source = resolve_source(mapping, args.source)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    cli_overrides = {field: getattr(args, f"col_{field}") for field in MAPPABLE_FIELDS}
    columns = resolve_columns(mapping, cli_overrides)
    date_formats = list(mapping.get("date_formats") or [])

    try:
        with csv_path.open("r", encoding=args.encoding, newline="") as fh:
            reader = csv.DictReader(fh)
            fieldnames = list(reader.fieldnames or [])
            try:
                _validate_csv_headers(fieldnames, columns, csv_path)
            except ValueError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 1
            csv_rows = list(reader)
    except UnicodeDecodeError as exc:
        print(
            f"error: cannot decode {csv_path} as {args.encoding}: {exc}. "
            f"Try a different encoding with --encoding (e.g. --encoding cp1252).",
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(f"error: cannot read {csv_path}: {exc}", file=sys.stderr)
        return 1

    today = datetime.now().date().isoformat()
    existing_active = _read_existing_or_empty(active_path)
    existing_archive = _read_existing_or_empty(archive_path)

    new_rows, n_active, n_archive, bad_dates = ingest(
        csv_rows,
        columns,
        source,
        date_formats,
        existing_active,
        existing_archive,
        today,
    )
    total_dupes = n_active + n_archive

    print(f"{source} fetched: {len(csv_rows)} record(s)")
    print(f"  new:    {len(new_rows)}")
    print(f"  dupes:  {total_dupes} ({n_active} active, {n_archive} archive)")
    for r in new_rows:
        print(f"  + {r['opportunity_id']} :: {r['title']}")

    if args.dry_run:
        print("(--dry-run: no files written)")
    elif not new_rows:
        print("(no new rows to write)")
    else:
        # Write target is active only; archive was read for dedup and must
        # not be echoed back into the active pipeline.
        write_rows_atomic(active_path, existing_active + new_rows)
        print(f"wrote {len(new_rows)} new row(s) to {active_path}")

    if bad_dates:
        seen: list[str] = []
        for v in bad_dates:
            if v not in seen:
                seen.append(v)
            if len(seen) >= 3:
                break
        sample_str = ", ".join(f"'{s}'" for s in seen)
        print(
            f"warning: {len(bad_dates)} unparseable date value(s); "
            f"fields left blank. Add a format to date_formats in {mapping_path}. "
            f"Sample values: {sample_str}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
