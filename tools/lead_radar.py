#!/usr/bin/env python3
"""
lead_radar.py — manage the Lead Radar tracker for broad upstream opportunities.

The active bid pipeline (bids/active/_pipeline.csv) is reserved for confirmed
mattress / product-fit bids. But many institutional buyers never issue a
standalone "mattress" RFP — they buy through broad cooperative / vendor-pool /
IDIQ vehicles (BuyBoard, TIPS, Choice Partners, Sourcewell, HGACBuy, OMNIA),
school-furniture / FF&E contracts, dorm / student-housing, correctional /
detention supply, shelter / emergency supply, and public-health residential
contracts. Lead Radar captures those upstream, review-worthy signals so the
hidden mattress demand is visible WITHOUT polluting the clean bid pipeline.

Leads live at leads/review/_lead_radar.csv and, once closed, move to
leads/archive/_lead_radar_archive.csv. A lead becomes an active bid ONLY when
a human explicitly runs `promote` with the confirmed product fit — broad
furniture / FF&E / co-op rows never auto-promote.

Subcommands:
    summary   Counts by status, source, and lead_type.
    list      Print review leads sorted by due_date (blank dates last).
    add       Append a new lead row (with validation).
    archive   Move a lead from review to the lead archive.
    promote   Copy a lead into bids/active/_pipeline.csv (requires
              --confirmed-products); marks the lead 'promoted' but keeps it.

Stdlib only. No third-party dependencies.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REVIEW = REPO_ROOT / "leads" / "review" / "_lead_radar.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "leads" / "archive" / "_lead_radar_archive.csv"
TEMPLATE_HEADER = REPO_ROOT / "templates" / "lead_radar_tracker.csv"

# Reuse the canonical bid-pipeline helpers for promotion so the two trackers
# never drift on id derivation or the active CSV's shape.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402

LEAD_HEADER = [
    "lead_id",
    "status",
    "source",
    "buyer",
    "solicitation_number",
    "title",
    "portal_url",
    "posted_date",
    "due_date",
    "lead_type",
    "trigger_terms",
    "fit_score",
    "next_action",
    "created_date",
    "last_reviewed",
    "notes",
]

DATE_FIELDS = ("posted_date", "due_date", "created_date", "last_reviewed")

STATUS_VALUES = ("watching", "reviewing", "promoted", "archived", "no-fit", "stale")
LEAD_TYPE_VALUES = (
    "co-op_contract_vehicle",
    "broad_furniture_ffe",
    "dorm_student_housing",
    "correctional_detention",
    "shelter_emergency",
    "public_health_residential",
    "awarded_contract_watch",
    "other",
)


# ---------------------------------------------------------------------
# CSV helpers (Lead Radar header; mirrors pipeline.read_rows/write_rows_atomic)
# ---------------------------------------------------------------------
def derive_lead_id(source: str, buyer: str, solicitation_number: str, title: str) -> str:
    """Stable lead id from source + buyer + solicitation/title (same rule the
    active pipeline uses for opportunity_id, so a promoted lead is traceable)."""
    return pipeline.derive_opportunity_id(source, buyer, solicitation_number, title)


# ---------------------------------------------------------------------
# Lead classification + row mapping
# ---------------------------------------------------------------------
# Shared by the ingest tools (ingest_email.py, ingest_rss.py) so REVIEW-band
# opportunities can be routed into Lead Radar WITHOUT duplicating the id rule
# or the CSV shape. The active bid pipeline stays strict (ACCEPT only); broad
# upstream signals land here for a human to triage.
def _lead_term_re(term: str) -> "re.Pattern[str]":
    """Whole-word/phrase matcher (spaces/hyphens interchangeable), so 'cot'
    never fires inside 'Scott' and 'tips' never inside 'fingertips'."""
    parts = re.split(r"[ \-]+", term)
    body = r"[\s\-]+".join(re.escape(p) for p in parts)
    return re.compile(r"(?<![A-Za-z0-9])" + body + r"(?![A-Za-z0-9])", re.IGNORECASE)


# Lead-type families in priority order: the first family whose term appears in
# the text wins, so classification is deterministic and conservative (no match
# -> "other").
#
# Specific institutional buyer/use contexts (dorm, correctional, shelter,
# public-health) come FIRST so they outrank a generic vehicle label — a
# "County Jail Furniture Vendor Pool" is more actionable as a correctional
# cluster than as a vendor pool. But the co-op/IDIQ/vendor-pool vehicle family
# still outranks generic furniture/FF&E, so a broad buying vehicle like an
# "Office Furniture Catalog (IDIQ)" keeps its vehicle-watch signal instead of
# collapsing to plain furniture.
_LEAD_TYPE_TERMS: list[tuple[str, list[str]]] = [
    ("dorm_student_housing", [
        "dorm", "dormitory", "residence hall", "student housing", "twin xl",
    ]),
    ("correctional_detention", [
        "jail", "jails", "prison", "prisons", "detention", "inmate",
        "correctional",
    ]),
    ("shelter_emergency", [
        "shelter", "emergency", "disaster", "cot", "cots",
    ]),
    ("public_health_residential", [
        "public health", "residential care", "behavioral health",
        "nursing home", "long-term care", "long term care",
    ]),
    ("co-op_contract_vehicle", [
        "buyboard", "tips", "choice partners", "sourcewell", "hgacbuy",
        "omnia", "vendor pool", "idiq", "cooperative", "co-op", "coop",
        "purchasing cooperative", "interlocal",
    ]),
    ("broad_furniture_ffe", [
        "furniture", "ff&e", "ffe", "furnishings", "casegoods", "case goods",
    ]),
]
_LEAD_TYPE_COMPILED = [
    (lead_type, [_lead_term_re(w) for w in words]) for lead_type, words in _LEAD_TYPE_TERMS
]


def classify_lead_type(text: str) -> str:
    """Bucket a lead into a lead_type from free text. First family to match in
    priority order wins; unmatched text is 'other'."""
    blob = text or ""
    for lead_type, patterns in _LEAD_TYPE_COMPILED:
        if any(rx.search(blob) for rx in patterns):
            return lead_type
    return "other"


def build_lead_row(opp_row: dict, verdict=None, today: str = "") -> dict:
    """Map a pipeline-style opportunity row (a REVIEW-band item) onto a Lead
    Radar row.

    opp_row uses active-pipeline field names (source, buyer,
    solicitation_number, title, portal_url, posted_date, due_date, fit_score,
    commodity_terms). lead_id reuses the canonical id rule so a later
    `promote` is traceable. `verdict`, when given, is a relevance.Verdict whose
    matched terms seed trigger_terms and whose reasons seed notes.
    """
    source = opp_row.get("source", "") or ""
    buyer = opp_row.get("buyer", "") or ""
    soln = opp_row.get("solicitation_number", "") or ""
    title = opp_row.get("title", "") or ""

    trigger_terms = ""
    notes = ""
    if verdict is not None:
        trigger_terms = "; ".join(getattr(verdict, "matched_include", []) or [])
        notes = "; ".join(getattr(verdict, "reasons", []) or [])

    blob = " ".join(p for p in (
        title, opp_row.get("commodity_terms", "") or "", trigger_terms, source, buyer
    ) if p)

    row = {k: "" for k in LEAD_HEADER}
    row.update({
        "lead_id": derive_lead_id(source, buyer, soln, title),
        "status": "reviewing",
        "source": source,
        "buyer": buyer,
        "solicitation_number": soln,
        "title": title,
        "portal_url": opp_row.get("portal_url", "") or "",
        "posted_date": opp_row.get("posted_date", "") or "",
        "due_date": opp_row.get("due_date", "") or "",
        "lead_type": classify_lead_type(blob),
        "trigger_terms": trigger_terms,
        "fit_score": opp_row.get("fit_score", "") or "",
        "next_action": "HUMAN: confirm mattress/bedding scope before promotion.",
        "created_date": today,
        "last_reviewed": today,
        "notes": notes,
    })
    return row


def lead_match_keys(row: dict) -> set[str]:
    """Stable dedup keys recognizing the same lead across the Lead Radar, the
    active pipeline, and the archive.

    Reads source/buyer/solicitation_number/title (and an explicit lead_id when
    present). The derived key uses the same rule as a promoted opportunity_id,
    so a lead matches an already-active bid with the same source+title even
    though the two trackers store different id columns.
    """
    keys: set[str] = set()
    source = (row.get("source") or "").strip()
    buyer = (row.get("buyer") or "").strip()
    soln = (row.get("solicitation_number") or "").strip()
    title = (row.get("title") or "").strip()

    explicit = (row.get("lead_id") or "").strip()
    if explicit:
        keys.add(f"lead:{explicit}")
    derived = derive_lead_id(source, buyer, soln, title)
    if derived and derived != "untitled":
        keys.add(f"lead:{derived}")
    if source and soln:
        keys.add(f"sol:{source.lower()}:{soln.lower()}")
    return keys


def _validate_date(value: str, field: str) -> None:
    if not value:
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field}: expected YYYY-MM-DD, got {value!r} ({exc})") from exc


def _validate_fit_score(value: int | None) -> None:
    if value is None:
        return
    if value < 0 or value > 100:
        raise ValueError(f"fit_score: expected integer 0..100, got {value!r}")


def read_lead_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (header, rows) for a Lead Radar CSV. Header must match LEAD_HEADER."""
    if not path.exists():
        raise FileNotFoundError(f"lead radar file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        if header != LEAD_HEADER:
            raise ValueError(
                f"{path}: header drifted from canonical.\n"
                f"  got:      {header}\n"
                f"  expected: {LEAD_HEADER}"
            )
        rows = [{k: (row.get(k) or "") for k in LEAD_HEADER} for row in reader]
    return header, rows


def write_lead_rows_atomic(path: Path, rows: Iterable[dict]) -> None:
    """Write CSV atomically: tmp file in same dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=LEAD_HEADER, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in LEAD_HEADER})
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
def cmd_summary(args: argparse.Namespace) -> int:
    review = Path(args.review)
    _, rows = read_lead_rows(review)

    print(f"Lead Radar: {review}")
    print(f"Total leads: {len(rows)}")
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
    print_counter("lead_type", "lead_type")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    review = Path(args.review)
    _, rows = read_lead_rows(review)

    def sort_key(row: dict) -> tuple:
        due = row.get("due_date") or ""
        return (1, "") if not due else (0, due)

    rows.sort(key=sort_key)

    if not rows:
        print(f"(no leads in {review})")
        return 0

    cols = ("lead_id", "status", "due_date", "lead_type", "fit_score", "buyer", "title")
    widths = {c: max(len(c), max((len(r.get(c, "")) for r in rows), default=0)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
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
        print(f"error: status {args.status!r} not in {list(STATUS_VALUES)}", file=sys.stderr)
        return 1
    if args.lead_type and args.lead_type not in LEAD_TYPE_VALUES:
        print(f"error: lead_type {args.lead_type!r} not in {list(LEAD_TYPE_VALUES)}", file=sys.stderr)
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
        print("error: one of --solicitation-number or --title is required to derive a lead_id",
              file=sys.stderr)
        return 1

    lead_id = args.lead_id or derive_lead_id(
        args.source, args.buyer, args.solicitation_number or "", args.title or ""
    )

    review = Path(args.review)
    if not review.exists():
        write_lead_rows_atomic(review, [])
    _, rows = read_lead_rows(review)

    existing_idx = next((i for i, r in enumerate(rows) if r.get("lead_id") == lead_id), None)
    if existing_idx is not None and not args.overwrite:
        print(f"error: lead_id {lead_id!r} already exists. Pass --overwrite to replace.",
              file=sys.stderr)
        return 1

    today = datetime.now().date().isoformat()
    new_row = {k: "" for k in LEAD_HEADER}
    new_row.update({
        "lead_id": lead_id,
        "status": args.status or "watching",
        "source": args.source,
        "buyer": args.buyer,
        "solicitation_number": args.solicitation_number or "",
        "title": args.title or "",
        "portal_url": args.portal_url or "",
        "posted_date": args.posted_date or "",
        "due_date": args.due_date or "",
        "lead_type": args.lead_type or "other",
        "trigger_terms": args.trigger_terms or "",
        "fit_score": str(args.fit_score) if args.fit_score is not None else "",
        "next_action": args.next_action or "",
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

    write_lead_rows_atomic(review, rows)
    print(f"{action} {lead_id} in {review}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    review = Path(args.review)
    archive = Path(args.archive)
    _, rows = read_lead_rows(review)

    idx = next((i for i, r in enumerate(rows) if r.get("lead_id") == args.lead_id), None)
    if idx is None:
        print(f"error: lead_id {args.lead_id!r} not found in {review}", file=sys.stderr)
        return 1

    if args.status and args.status not in STATUS_VALUES:
        print(f"error: status {args.status!r} not in {list(STATUS_VALUES)}", file=sys.stderr)
        return 1

    moved_row = rows.pop(idx)
    # Default to the terminal 'archived' status unless the caller set a more
    # specific close reason (no-fit / stale).
    moved_row["status"] = args.status or "archived"
    if args.next_action is not None:
        moved_row["next_action"] = args.next_action
    if args.note:
        existing = moved_row.get("notes") or ""
        moved_row["notes"] = f"{existing}; {args.note}" if existing else args.note
    moved_row["last_reviewed"] = datetime.now().date().isoformat()

    if not archive.exists():
        write_lead_rows_atomic(archive, [])
    _, archive_rows = read_lead_rows(archive)

    archive_idx = next((i for i, r in enumerate(archive_rows) if r.get("lead_id") == args.lead_id), None)
    if archive_idx is not None:
        archive_rows[archive_idx] = moved_row
    else:
        archive_rows.append(moved_row)

    # Write and verify the archive before removing the row from review, so a
    # failed second write never loses the lead.
    write_lead_rows_atomic(archive, archive_rows)
    _, verified = read_lead_rows(archive)
    if not any(r.get("lead_id") == args.lead_id for r in verified):
        print(f"error: archive write did not persist {args.lead_id!r}; review left unchanged",
              file=sys.stderr)
        return 1
    write_lead_rows_atomic(review, rows)
    print(f"archived {args.lead_id} from {review} to {archive} (status={moved_row['status']})")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    review = Path(args.review)
    active = Path(args.active)
    _, rows = read_lead_rows(review)

    idx = next((i for i, r in enumerate(rows) if r.get("lead_id") == args.lead_id), None)
    if idx is None:
        print(f"error: lead_id {args.lead_id!r} not found in {review}", file=sys.stderr)
        return 1
    lead = rows[idx]

    # argparse marks --confirmed-products required, but guard anyway: a broad
    # lead must NEVER become an active bid without a human stating the fit.
    confirmed = (args.confirmed_products or "").strip()
    if not confirmed:
        print("error: --confirmed-products is required to promote a lead to the active "
              "bid pipeline (e.g. --confirmed-products \"mattresses; bed frames\")",
              file=sys.stderr)
        return 1

    opportunity_id = pipeline.derive_opportunity_id(
        lead.get("source", ""), lead.get("buyer", ""),
        lead.get("solicitation_number", ""), lead.get("title", ""),
    )

    if not active.exists():
        pipeline.write_rows_atomic(active, [])
    _, active_rows = pipeline.read_rows(active)

    today = datetime.now().date().isoformat()
    already = any((r.get("opportunity_id") or "").strip() == opportunity_id for r in active_rows)
    if already:
        print(f"note: {opportunity_id!r} already in active pipeline; not duplicating.")
    else:
        new_row = {k: "" for k in pipeline.CANONICAL_HEADER}
        new_row.update({
            "opportunity_id": opportunity_id,
            "status": "watching",
            "source": lead.get("source", ""),
            "buyer": lead.get("buyer", ""),
            "solicitation_number": lead.get("solicitation_number", ""),
            "title": lead.get("title", ""),
            "portal_url": lead.get("portal_url", ""),
            "posted_date": lead.get("posted_date", ""),
            "due_date": lead.get("due_date", ""),
            "primary_products": confirmed,
            "commodity_terms": lead.get("trigger_terms", ""),
            "fit_score": lead.get("fit_score", ""),
            "next_action": "Promoted from Lead Radar — confirm scope, run pipeline.py score, decide bid/no-bid",
            "created_date": today,
            "last_reviewed": today,
            "notes": f"Promoted from Lead Radar lead {args.lead_id}",
        })
        active_rows.append(new_row)
        pipeline.write_rows_atomic(active, active_rows)

    # Mark the lead promoted (kept, not deleted) for traceability.
    lead["status"] = "promoted"
    lead["last_reviewed"] = today
    note = f"promoted to active pipeline as {opportunity_id} on {today}"
    lead["notes"] = f"{lead['notes']}; {note}" if lead.get("notes") else note
    write_lead_rows_atomic(review, rows)

    verb = "linked existing" if already else "promoted"
    print(f"{verb} lead {args.lead_id} -> active opportunity {opportunity_id}")
    print(f"  confirmed_products: {confirmed}")
    return 0


# ---------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", default=str(DEFAULT_REVIEW), help="Lead Radar review CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Lead Radar archive CSV (default: %(default)s)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_sum = sub.add_parser("summary", help="Counts by status, source, and lead_type.")
    p_sum.set_defaults(func=cmd_summary)

    p_list = sub.add_parser("list", help="Print review leads sorted by due_date.")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Append a new lead row.")
    p_add.set_defaults(func=cmd_add)
    p_add.add_argument("--lead-id", help="Explicit id; derived from source+buyer+solicitation/title if omitted.")
    p_add.add_argument("--status", help=f"One of {list(STATUS_VALUES)} (default: watching)")
    p_add.add_argument("--source", required=True)
    p_add.add_argument("--buyer", required=True)
    p_add.add_argument("--solicitation-number", default="")
    p_add.add_argument("--title", default="")
    p_add.add_argument("--portal-url", default="")
    p_add.add_argument("--posted-date", default="")
    p_add.add_argument("--due-date", default="")
    p_add.add_argument("--lead-type", help=f"One of {list(LEAD_TYPE_VALUES)} (default: other)")
    p_add.add_argument("--trigger-terms", default="", help="Relevance terms that surfaced this lead (e.g. 'furniture; ff&e').")
    p_add.add_argument("--fit-score", type=int, default=None)
    p_add.add_argument("--next-action", default="")
    p_add.add_argument("--created-date", default="")
    p_add.add_argument("--last-reviewed", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--overwrite", action="store_true", help="Replace an existing lead with the same lead_id.")

    p_arc = sub.add_parser("archive", help="Move a lead from review to the lead archive.")
    p_arc.set_defaults(func=cmd_archive)
    p_arc.add_argument("lead_id", help="Lead id to archive.")
    p_arc.add_argument("--status", default=None, help=f"Close status (default: archived). One of {list(STATUS_VALUES)}.")
    p_arc.add_argument("--next-action", default=None, help="Replace next_action on the archived lead. Pass '' to clear.")
    p_arc.add_argument("--note", default=None, help="Append text to the notes column (separator '; ').")

    p_promote = sub.add_parser(
        "promote",
        help="Copy a lead into the active bid pipeline (requires --confirmed-products).",
    )
    p_promote.set_defaults(func=cmd_promote)
    p_promote.add_argument("lead_id", help="Lead id to promote.")
    p_promote.add_argument(
        "--confirmed-products",
        required=True,
        help="Human-confirmed product fit for the active bid, e.g. 'mattresses; bed frames'. "
             "Required: broad furniture/FF&E/co-op leads never auto-promote.",
    )
    p_promote.add_argument("--active", default=str(pipeline.DEFAULT_ACTIVE), help="Active bid pipeline CSV (default: %(default)s)")

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
