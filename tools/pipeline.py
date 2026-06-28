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
    summary          Counts by status, source, risk_level, and procurement_risk.
    score            Recompute fit_score; fill blank risk_level unless told to overwrite.
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

# relevance.py is the single source of truth for mattress fit scoring; it lives
# alongside this module. Make it importable whether pipeline runs as a script
# or is imported by another tool.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relevance  # noqa: E402


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
    "procurement_risk",
    "gate_status",
    "compliance_blocker",
    "win_score",
    "win_factors",
]

DATE_FIELDS = ("posted_date", "question_deadline", "due_date", "created_date", "last_reviewed")

STATUS_VALUES = ("watching", "drafting", "submitted", "awarded", "lost", "no-bid", "cancelled")
RISK_LEVEL_VALUES = ("low", "medium", "high")
PROCUREMENT_RISK_VALUES = ("low", "medium", "high", "blocker")
GATE_STATUS_VALUES = ("triage", "blocked", "bid_ready", "drafting", "submitted", "closed")

# The `score` subcommand's fit scoring is delegated to relevance.classify
# (see score_text), so the pipeline computes fit_score the same whole-word way
# every ingest channel already does. The old substring keyword vocabularies
# (POSITIVE_KEYWORDS/CAUTION_KEYWORDS/STRONG_CAUTION + weights) were retired:
# they re-scored ingested rows with a `.count()` substring scorer that both
# clobbered the relevance-derived score and false-fired on "foundation"/"cot".


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


def _parse_iso_date(value: str) -> str:
    try:
        _validate_date(value, "date")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    return value


def _validate_fit_score(value: int | None) -> None:
    """Raise ValueError if fit_score is present and outside 0..100."""
    if value is None:
        return
    if value < 0 or value > 100:
        raise ValueError(f"fit_score: expected integer 0..100, got {value!r}")


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (header, rows) for a pipeline CSV.

    Older pipeline CSVs may be missing newly appended optional columns.
    Those are accepted and normalized to blank values in memory; unknown
    or reordered columns still fail because that can corrupt operator data.
    """
    if not path.exists():
        raise FileNotFoundError(f"pipeline file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        expected_prefix = CANONICAL_HEADER[:len(header)]
        if header != expected_prefix:
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

def _win_score_int(row: dict) -> int | None:
    """Parse a row's stored win_score to int, or None when blank/unparseable."""
    raw = (row.get("win_score") or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def cmd_list(args: argparse.Namespace) -> int:
    active = Path(args.active)
    _, rows = read_rows(active)

    def due_sort_key(row: dict) -> tuple:
        due = row.get("due_date") or ""
        # Blanks last: prefix tuple with a flag so empty strings sort after.
        return (1, "") if not due else (0, due)

    def win_sort_key(row: dict) -> tuple:
        # win_score DESC (blanks last), due_date ASC tiebreak (blanks last).
        ws = _win_score_int(row)
        ws_key = (1, 0) if ws is None else (0, -ws)
        return (ws_key, due_sort_key(row))

    if getattr(args, "sort", "win") == "due":
        rows.sort(key=due_sort_key)
    else:
        rows.sort(key=win_sort_key)

    if not rows:
        print(f"(no rows in {active})")
        return 0

    cols = (
        "opportunity_id",
        "status",
        "win_score",
        "due_date",
        "fit_score",
        "risk_level",
        "procurement_risk",
        "gate_status",
        "buyer",
        "title",
    )
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
    if args.risk_level and args.risk_level not in RISK_LEVEL_VALUES:
        print(
            f"error: risk_level {args.risk_level!r} not in {list(RISK_LEVEL_VALUES)}",
            file=sys.stderr,
        )
        return 1
    if args.procurement_risk and args.procurement_risk not in PROCUREMENT_RISK_VALUES:
        print(
            f"error: procurement_risk {args.procurement_risk!r} not in {list(PROCUREMENT_RISK_VALUES)}",
            file=sys.stderr,
        )
        return 1
    if args.gate_status and args.gate_status not in GATE_STATUS_VALUES:
        print(
            f"error: gate_status {args.gate_status!r} not in {list(GATE_STATUS_VALUES)}",
            file=sys.stderr,
        )
        return 1
    try:
        _validate_fit_score(args.fit_score)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
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
        "procurement_risk": args.procurement_risk or "",
        "gate_status": args.gate_status or "",
        "compliance_blocker": args.compliance_blocker or "",
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
    print_counter("procurement_risk", "procurement_risk")
    print_counter("gate_status", "gate_status")
    return 0


def score_text(text: str) -> tuple[int, str, dict]:
    """Return (fit_score 0..100, risk_level, detail dict).

    Delegates to relevance.classify so the pipeline's fit_score is computed the
    SAME whole-word way every ingest channel already assigns it — re-scoring an
    ingested row no longer clobbers its relevance-derived score, and there are
    no substring false-fires (the retired scorer's "foundation"/"cot"/"bunk").
    relevance is the single source of truth for fit_score.

    risk_level is a coarse triage band off the relevance decision:
      ACCEPT with high confidence -> low; ACCEPT/REVIEW mid -> medium;
      REJECT or very low confidence -> high.
    """
    verdict = relevance.classify(text)
    score = verdict.confidence

    if verdict.decision == "ACCEPT" and score >= 75:
        risk = "low"
    elif verdict.decision in ("ACCEPT", "REVIEW") and score >= 25:
        risk = "medium"
    else:
        risk = "high"

    return score, risk, {
        "decision": verdict.decision,
        "matched_include": verdict.matched_include,
        "matched_exclude": verdict.matched_exclude,
        "context": verdict.context,
    }


def cmd_score(args: argparse.Namespace) -> int:
    active = Path(args.active)
    _, rows = read_rows(active)

    updates: list[tuple[dict, int, str, str, str]] = []
    for row in rows:
        if args.only_created_date and row.get("created_date") != args.only_created_date:
            continue
        text_blob = " ".join(
            row.get(field, "") or ""
            for field in ("title", "primary_products", "commodity_terms")
        )
        new_score, suggested_risk, _detail = score_text(text_blob)
        old_score = row.get("fit_score") or ""
        old_risk = row.get("risk_level") or ""
        new_risk = suggested_risk if args.overwrite_risk or not old_risk else old_risk
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


def cmd_win_score(args: argparse.Namespace) -> int:
    """Recompute the composite win_score (+ win_factors) for each row.

    Mirrors cmd_score: relevance.classify stays the product-fit source; this
    layers value/winnability/strategic factors on top via win_score.compute and
    writes the two appended columns. Sort order (cmd_list/digest) then surfaces
    the best opportunities first."""
    import win_score  # local import keeps the module pair decoupled at load time

    active = Path(args.active)
    _, rows = read_rows(active)
    today = datetime.now().date()

    updates: list[tuple[dict, str, str, str, str]] = []
    for row in rows:
        if args.only_created_date and row.get("created_date") != args.only_created_date:
            continue
        score, factors = win_score.compute(row, today)
        new_score = str(score)
        new_factors = win_score.format_factors(factors)
        old_score = row.get("win_score") or ""
        old_factors = row.get("win_factors") or ""
        if new_score != old_score or new_factors != old_factors:
            updates.append((row, new_score, new_factors, old_score, old_factors))

    if not updates:
        print("win-score: no changes (all rows already in sync).")
        return 0

    print(f"win-score: {len(updates)} row(s) would change:")
    for row, new_score, new_factors, old_score, _ in updates:
        print(
            f"  {row['opportunity_id']}: "
            f"win_score {old_score or '-'} -> {new_score}  [{new_factors}]"
        )

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0

    today_iso = today.isoformat()
    for row, new_score, new_factors, _, _ in updates:
        row["win_score"] = new_score
        row["win_factors"] = new_factors
        row["last_reviewed"] = today_iso
    write_rows_atomic(active, rows)
    print(f"win-score: wrote {active}")
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

    # Write and verify the archive before removing the row from active.
    # If the second write fails, the row may be duplicated, but it is not
    # lost; the archived copy remains the recovery point.
    write_rows_atomic(archive, archive_rows)
    _, verified_archive_rows = read_rows(archive)
    if not any(r.get("opportunity_id") == args.opportunity_id for r in verified_archive_rows):
        print(
            f"error: archive write did not persist {args.opportunity_id!r}; active left unchanged",
            file=sys.stderr,
        )
        return 1
    write_rows_atomic(active, rows)
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

    p_list = sub.add_parser("list", help="Print active rows ranked by win_score (or due_date).")
    p_list.set_defaults(func=cmd_list)
    p_list.add_argument(
        "--sort",
        choices=("win", "due"),
        default="win",
        help="Sort key: win_score desc (default) or due_date asc.",
    )

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
    p_add.add_argument("--procurement-risk", default="")
    p_add.add_argument("--gate-status", default="")
    p_add.add_argument("--compliance-blocker", default="")
    p_add.add_argument("--next-action", default="")
    p_add.add_argument("--owner", default="")
    p_add.add_argument("--created-date", default="")
    p_add.add_argument("--last-reviewed", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--overwrite", action="store_true", help="Replace an existing row with the same opportunity_id.")

    p_sum = sub.add_parser("summary", help="Counts by status, source, and risk_level.")
    p_sum.set_defaults(func=cmd_summary)

    p_score = sub.add_parser("score", help="Recompute fit_score; fill blank risk_level unless told to overwrite.")
    p_score.set_defaults(func=cmd_score)
    p_score.add_argument("--dry-run", action="store_true", help="Show changes without writing.")
    p_score.add_argument(
        "--only-created-date",
        type=_parse_iso_date,
        default="",
        help="Only score rows with this created_date (YYYY-MM-DD), useful for ingest automation.",
    )
    p_score.add_argument(
        "--overwrite-risk",
        action="store_true",
        help="Also replace existing risk_level values with the scorer's suggestion.",
    )

    p_win = sub.add_parser("win-score", help="Recompute the composite win_score + win_factors.")
    p_win.set_defaults(func=cmd_win_score)
    p_win.add_argument("--dry-run", action="store_true", help="Show changes without writing.")
    p_win.add_argument(
        "--only-created-date",
        type=_parse_iso_date,
        default="",
        help="Only score rows with this created_date (YYYY-MM-DD), useful for ingest automation.",
    )

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
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
