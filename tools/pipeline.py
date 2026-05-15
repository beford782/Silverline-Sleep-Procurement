#!/usr/bin/env python3
"""
pipeline.py — manage the bid opportunity pipeline tracker.

The live pipeline lives at bids/active/_pipeline.csv. When an
opportunity closes (awarded, lost, no-bid, cancelled) it moves to
bids/archive/_pipeline_archive.csv. Both files share the canonical
header defined in templates/opportunity_tracker.csv.

Subcommands:
    list             Print the active pipeline sorted by due_date (blank dates last).
    add              Append a new opportunity row.
    summary          Counts by status, source, and risk_level.
    score            Recompute fit_score and risk_level from text columns.
    move-to-archive  Move a row from active to archive.

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"
TEMPLATE_HEADER = REPO_ROOT / "templates" / "opportunity_tracker.csv"

CANONICAL_HEADER = [
    "opportunity_id",
    "status",
    "source",
    "buyer",
    "solicitation_number",
    "title",
    "portal_url",
    "posted_date",
    "question_deadline",
    "due_date",
    "delivery_location",
    "estimated_value",
    "primary_products",
    "commodity_terms",
    "fit_score",
    "risk_level",
    "next_action",
    "owner",
    "created_date",
    "last_reviewed",
    "notes",
]

DATE_FIELDS = ("posted_date", "question_deadline", "due_date", "created_date", "last_reviewed")

STATUS_VALUES = ("watching", "drafting", "submitted", "awarded", "lost", "no-bid", "cancelled")

# Keyword vocabularies used by the `score` subcommand. Kept transparent
# and tunable here — no ML.
POSITIVE_KEYWORDS = (
    "mattress",
    "mattresses",
    "bedding",
    "box spring",
    "foundation",
    "bed frame",
    "bunk",
    "cot",
    "dormitory",
    "residence hall",
    "correctional",
    "jail",
    "prison",
    "detention",
    "shelter",
    "emergency",
    "medical",
    "healthcare",
    "hospital",
    "institutional furniture",
    "ff&e",
)

CAUTION_KEYWORDS = (
    "anti-ligature",
    "removal",
    "disposal",
    "inside delivery",
    "installation",
    "nationwide",
    "laundry",
    "sheets",
    "pillows",
    "bunk beds",
    "fixed price",
    "multi-year",
    "liquidated damages",
    # Calibration from real SAM.gov ingest: these federal-data patterns
    # were repeatedly producing false-positive mattress matches.
    "aircraft",              # military aviation hardware, not bedding
    "concrete",              # civil-engineering "concrete mattress" (erosion mat)
    "inspection services",   # buyer wants an inspector, not a manufacturer
    "refinish",              # furniture refurbishment, not new bedding
    "reupholster",           # furniture refurbishment
    "overseas",              # outside vendor service geography
)

# Strong-caution keywords force the row to high-risk regardless of score.
STRONG_CAUTION = ("anti-ligature", "liquidated damages", "nationwide")

# Weights tuned against real SAM.gov titles, which are typically terse
# (1-2 keyword hits). At weight 25, one positive hit lands at the
# medium-risk threshold; two hits land at the bottom of low.
POSITIVE_WEIGHT = 25
CAUTION_WEIGHT = 25


def slugify(text: str) -> str:
    """Lowercase, dash-separated, alphanumerics only."""
    out = re.sub(r"[^a-z0-9]+", "-", text.strip().lower())
    return out.strip("-") or "untitled"


def derive_opportunity_id(source: str, buyer: str, solicitation_number: str, title: str) -> str:
    label = solicitation_number or title
    parts = [slugify(p) for p in (source, buyer, label) if p]
    raw = "-".join(parts)
    # Collapse repeated dashes that emerge when joined.
    return re.sub(r"-+", "-", raw).strip("-") or "untitled"


def _validate_date(value: str, field: str) -> None:
    """Raise ValueError if value is non-empty and not YYYY-MM-DD."""
    if not value:
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field}: expected YYYY-MM-DD, got {value!r} ({exc})") from exc


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (header, rows) for a pipeline CSV. Header must match CANONICAL_HEADER."""
    if not path.exists():
        raise FileNotFoundError(f"pipeline file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        if header != CANONICAL_HEADER:
            raise ValueError(
                f"{path}: header drifted from canonical.\n"
                f"  got:      {header}\n"
                f"  expected: {CANONICAL_HEADER}"
            )
        rows = [{k: (row.get(k) or "") for k in CANONICAL_HEADER} for row in reader]
    return header, rows


def write_rows_atomic(path: Path, rows: Iterable[dict]) -> None:
    """Write CSV atomically: tmp file in same dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CANONICAL_HEADER, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in CANONICAL_HEADER})
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------

def cmd_list(args: argparse.Namespace) -> int:
    active = Path(args.active)
    _, rows = read_rows(active)

    def sort_key(row: dict) -> tuple:
        due = row.get("due_date") or ""
        # Blanks last: prefix tuple with a flag so empty strings sort after.
        return (1, "") if not due else (0, due)

    rows.sort(key=sort_key)

    if not rows:
        print(f"(no rows in {active})")
        return 0

    cols = ("opportunity_id", "status", "due_date", "fit_score", "risk_level", "buyer", "title")
    widths = {c: max(len(c), max((len(r.get(c, "")) for r in rows), default=0)) for c in cols}
    header_line = "  ".join(c.ljust(widths[c]) for c in cols)
    sep_line = "  ".join("-" * widths[c] for c in cols)
    print(header_line)
    print(sep_line)
    for r in rows:
        print("  ".join((r.get(c, "") or "").ljust(widths[c]) for c in cols))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    for field in DATE_FIELDS:
        try:
            _validate_date(getattr(args, field) or "", field)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    if args.status and args.status not in STATUS_VALUES:
        print(
            f"error: status {args.status!r} not in {list(STATUS_VALUES)}",
            file=sys.stderr,
        )
        return 1

    if not args.source:
        print("error: --source is required", file=sys.stderr)
        return 1
    if not args.buyer:
        print("error: --buyer is required", file=sys.stderr)
        return 1
    if not (args.solicitation_number or args.title):
        print(
            "error: one of --solicitation-number or --title is required to derive an id",
            file=sys.stderr,
        )
        return 1

    opportunity_id = args.opportunity_id or derive_opportunity_id(
        args.source, args.buyer, args.solicitation_number or "", args.title or ""
    )

    active = Path(args.active)
    if not active.exists():
        write_rows_atomic(active, [])

    _, rows = read_rows(active)
    existing_idx = next(
        (i for i, r in enumerate(rows) if r.get("opportunity_id") == opportunity_id),
        None,
    )
    if existing_idx is not None and not args.overwrite:
        print(
            f"error: opportunity_id {opportunity_id!r} already exists. "
            f"Pass --overwrite to replace.",
            file=sys.stderr,
        )
        return 1

    today = datetime.now().date().isoformat()
    new_row = {k: "" for k in CANONICAL_HEADER}
    new_row.update({
        "opportunity_id": opportunity_id,
        "status": args.status or "watching",
        "source": args.source,
        "buyer": args.buyer,
        "solicitation_number": args.solicitation_number or "",
        "title": args.title or "",
        "portal_url": args.portal_url or "",
        "posted_date": args.posted_date or "",
        "question_deadline": args.question_deadline or "",
        "due_date": args.due_date or "",
        "delivery_location": args.delivery_location or "",
        "estimated_value": str(args.estimated_value) if args.estimated_value is not None else "",
        "primary_products": args.primary_products or "",
        "commodity_terms": args.commodity_terms or "",
        "fit_score": str(args.fit_score) if args.fit_score is not None else "",
        "risk_level": args.risk_level or "",
        "next_action": args.next_action or "",
        "owner": args.owner or "",
        "created_date": args.created_date or today,
        "last_reviewed": args.last_reviewed or today,
        "notes": args.notes or "",
    })

    if existing_idx is not None:
        rows[existing_idx] = new_row
        action = "replaced"
    else:
        rows.append(new_row)
        action = "added"

    write_rows_atomic(active, rows)
    print(f"{action} {opportunity_id} in {active}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    active = Path(args.active)
    _, rows = read_rows(active)

    print(f"Pipeline: {active}")
    print(f"Total rows: {len(rows)}")
    print()

    def print_counter(label: str, key: str) -> None:
        counter = Counter((r.get(key) or "(blank)") for r in rows)
        print(f"By {label}:")
        if not counter:
            print("  (none)")
            return
        for value, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {count:>3}  {value}")
        print()

    print_counter("status", "status")
    print_counter("source", "source")
    print_counter("risk_level", "risk_level")
    return 0


def score_text(text: str) -> tuple[int, str, dict]:
    """Return (clamped_score 0..100, risk_level, detail dict)."""
    lowered = text.lower()
    positive_hits = sum(lowered.count(kw) for kw in POSITIVE_KEYWORDS)
    caution_hits = sum(lowered.count(kw) for kw in CAUTION_KEYWORDS)
    strong_caution = any(kw in lowered for kw in STRONG_CAUTION)

    raw = positive_hits * POSITIVE_WEIGHT - caution_hits * CAUTION_WEIGHT
    score = max(0, min(100, raw))

    if strong_caution or score < 25:
        risk = "high"
    elif score < 75:
        risk = "medium"
    else:
        risk = "low"

    return score, risk, {
        "positive_hits": positive_hits,
        "caution_hits": caution_hits,
        "strong_caution": strong_caution,
    }


def cmd_score(args: argparse.Namespace) -> int:
    active = Path(args.active)
    _, rows = read_rows(active)

    updates: list[tuple[dict, int, str, int, str]] = []
    for row in rows:
        text_blob = " ".join(
            row.get(field, "") or ""
            for field in ("title", "primary_products", "commodity_terms", "notes")
        )
        new_score, new_risk, _detail = score_text(text_blob)
        old_score = row.get("fit_score") or ""
        old_risk = row.get("risk_level") or ""
        if str(new_score) != old_score or new_risk != old_risk:
            updates.append((row, new_score, new_risk, old_score, old_risk))

    if not updates:
        print("score: no changes (all rows already in sync).")
        return 0

    print(f"score: {len(updates)} row(s) would change:")
    for row, new_score, new_risk, old_score, old_risk in updates:
        print(
            f"  {row['opportunity_id']}: "
            f"fit_score {old_score or '-'} -> {new_score}, "
            f"risk_level {old_risk or '-'} -> {new_risk}"
        )

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0

    today = datetime.now().date().isoformat()
    for row, new_score, new_risk, _, _ in updates:
        row["fit_score"] = str(new_score)
        row["risk_level"] = new_risk
        row["last_reviewed"] = today
    write_rows_atomic(active, rows)
    print(f"score: wrote {active}")
    return 0


def cmd_move_to_archive(args: argparse.Namespace) -> int:
    active = Path(args.active)
    archive = Path(args.archive)
    _, rows = read_rows(active)

    idx = next((i for i, r in enumerate(rows) if r.get("opportunity_id") == args.opportunity_id), None)
    if idx is None:
        print(f"error: opportunity_id {args.opportunity_id!r} not found in {active}", file=sys.stderr)
        return 1

    if args.status and args.status not in STATUS_VALUES:
        print(
            f"error: status {args.status!r} not in {list(STATUS_VALUES)}",
            file=sys.stderr,
        )
        return 1

    moved_row = rows.pop(idx)

    metadata_changed = False
    if args.status:
        moved_row["status"] = args.status
        metadata_changed = True
    if args.next_action is not None:
        moved_row["next_action"] = args.next_action
        metadata_changed = True
    if args.note:
        existing = moved_row.get("notes") or ""
        moved_row["notes"] = f"{existing}; {args.note}" if existing else args.note
        metadata_changed = True
    if metadata_changed:
        moved_row["last_reviewed"] = datetime.now().date().isoformat()

    if not archive.exists():
        write_rows_atomic(archive, [])
    _, archive_rows = read_rows(archive)

    # Refuse to duplicate in the archive; replace if already there.
    archive_idx = next(
        (i for i, r in enumerate(archive_rows) if r.get("opportunity_id") == args.opportunity_id),
        None,
    )
    if archive_idx is not None:
        archive_rows[archive_idx] = moved_row
    else:
        archive_rows.append(moved_row)

    write_rows_atomic(active, rows)
    write_rows_atomic(archive, archive_rows)
    print(f"moved {args.opportunity_id} from {active} to {archive}")
    return 0


# ---------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Archive pipeline CSV (default: %(default)s)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="Print active rows sorted by due_date.")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Append a new opportunity row.")
    p_add.set_defaults(func=cmd_add)
    p_add.add_argument("--opportunity-id", help="Explicit id; derived from source+buyer+solicitation/title if omitted.")
    p_add.add_argument("--status", help=f"One of {list(STATUS_VALUES)} (default: watching)")
    p_add.add_argument("--source", required=True)
    p_add.add_argument("--buyer", required=True)
    p_add.add_argument("--solicitation-number", default="")
    p_add.add_argument("--title", default="")
    p_add.add_argument("--portal-url", default="")
    p_add.add_argument("--posted-date", default="")
    p_add.add_argument("--question-deadline", default="")
    p_add.add_argument("--due-date", default="")
    p_add.add_argument("--delivery-location", default="")
    p_add.add_argument("--estimated-value", type=float, default=None)
    p_add.add_argument("--primary-products", default="")
    p_add.add_argument("--commodity-terms", default="")
    p_add.add_argument("--fit-score", type=int, default=None)
    p_add.add_argument("--risk-level", default="")
    p_add.add_argument("--next-action", default="")
    p_add.add_argument("--owner", default="")
    p_add.add_argument("--created-date", default="")
    p_add.add_argument("--last-reviewed", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--overwrite", action="store_true", help="Replace an existing row with the same opportunity_id.")

    p_sum = sub.add_parser("summary", help="Counts by status, source, and risk_level.")
    p_sum.set_defaults(func=cmd_summary)

    p_score = sub.add_parser("score", help="Recompute fit_score and risk_level from text columns.")
    p_score.set_defaults(func=cmd_score)
    p_score.add_argument("--dry-run", action="store_true", help="Show changes without writing.")

    p_arc = sub.add_parser("move-to-archive", help="Move a row from active to archive.")
    p_arc.set_defaults(func=cmd_move_to_archive)
    p_arc.add_argument("opportunity_id", help="Opportunity id to move.")
    p_arc.add_argument(
        "--status",
        default=None,
        help=f"Set close status on the archived row. One of {list(STATUS_VALUES)}.",
    )
    p_arc.add_argument(
        "--next-action",
        default=None,
        help="Replace next_action on the archived row. Pass '' to clear.",
    )
    p_arc.add_argument(
        "--note",
        default=None,
        help="Append text to the notes column (separator '; '). Empty notes are set rather than prefixed.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
