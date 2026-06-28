#!/usr/bin/env python3
"""
demand_radar.py — manage the Demand Radar tracker for pre-RFP mattress demand.

Where Lead Radar (tools/lead_radar.py) captures broad upstream PROCUREMENT
signals (co-op vehicles, FF&E contracts, vendor pools) and the active bid
pipeline (bids/active/_pipeline.csv) holds confirmed mattress bids, Demand Radar
sits one step EARLIER than either: it tracks construction / real-estate signals
that a new pile of institutional beds is about to exist — a hotel breaking
ground, a senior-living community opening, a student-housing tower under
construction, a county jail, a shelter — BEFORE any solicitation is posted.

Demand Radar is architecturally PARALLEL to Lead Radar and NEVER touches the bid
pipeline. There is no `promote` here: a pre-RFP demand signal has no
solicitation yet, so the human handoff is `outreach` (reach the developer / GC /
FF&E firm / owner), not a bid. Rows live at leads/demand/_demand_radar.csv and,
once closed, move to leads/demand/_demand_radar_archive.csv.

Subcommands:
    summary   Counts by status, segment, project_stage; plus buy-windows in the
              next 180 days (sorted ascending; blank windows last).
    list      Print demand rows (optionally filtered by --status/--segment).
    add       Append a new demand row (with validation).
    archive   Move a demand row from review to the demand archive.
    outreach  Human handoff: mark a row 'outreach', stamp the contact + note,
              and set a dated follow-up. Never writes the bid pipeline.

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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REVIEW = REPO_ROOT / "leads" / "demand" / "_demand_radar.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "leads" / "demand" / "_demand_radar_archive.csv"
TEMPLATE_HEADER = REPO_ROOT / "templates" / "demand_radar_tracker.csv"

DEMAND_HEADER = [
    "demand_id",
    "status",
    "segment",
    "facility_name",
    "owner_operator",
    "location",
    "scale",
    "project_stage",
    "est_buy_window",
    "est_completion_date",
    "signal_source",
    "source_url",
    "first_seen",
    "last_reviewed",
    "est_value",
    "next_action",
    "notes",
]

SEGMENT_VALUES = ("hotel", "senior-living", "student-housing", "healthcare",
                  "correctional", "shelter")
STAGE_VALUES = ("planned", "proposed", "under-construction", "renovation",
                "opening", "delivered")
STATUS_VALUES = ("watching", "reviewing", "outreach", "converted", "no-fit",
                 "stale", "archived")

# est_completion_date may be "", "YYYY-MM-DD", or a bare "YYYY". first_seen and
# last_reviewed are "" or "YYYY-MM-DD". est_buy_window is "" or "YYYY-MM".
DATE_FIELDS = ("est_completion_date", "first_seen", "last_reviewed")

_YEAR_RE = re.compile(r"\d{4}")


# ---------------------------------------------------------------------
# Identity (no solicitation number exists pre-RFP, so identity is
# source + segment + facility/location). Self-contained slug rule mirroring
# pipeline.slugify so Demand Radar never imports — and therefore never touches —
# the bid pipeline.
# ---------------------------------------------------------------------
def _slugify(text: str) -> str:
    """Lowercase, dash-separated, alphanumerics only."""
    out = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower())
    return out.strip("-")


def demand_id_for(source: str, segment: str, facility_name: str, location: str) -> str:
    """Stable demand id from source + segment + facility/location. Pre-RFP
    signals carry NO solicitation number, so identity is the facility itself."""
    parts = [_slugify(p) for p in (source, segment, facility_name, location) if _slugify(p)]
    raw = "-".join(parts)
    return re.sub(r"-+", "-", raw).strip("-") or "untitled"


# ---------------------------------------------------------------------
# DemandVerdict -> row mapping
# ---------------------------------------------------------------------
def build_demand_row(entry_title: str, source: str, verdict, today: str = "",
                     source_url: str = "") -> dict:
    """Map a demand_signal.DemandVerdict + a feed entry onto a Demand Radar row.

    `entry_title` is the headline/title of the construction/real-estate signal;
    it is stored as facility_name (best-effort) for now. `verdict` is a
    demand_signal.DemandVerdict whose segment / scale / project_stage /
    est_buy_window / est_completion_date / states / reasons populate the row.
    """
    segment = getattr(verdict, "segment", "") or ""
    scale_value = getattr(verdict, "scale_value", None)
    scale_unit = getattr(verdict, "scale_unit", "") or ""
    project_stage = getattr(verdict, "project_stage", "") or ""
    est_buy_window = getattr(verdict, "est_buy_window", "") or ""
    est_completion_date = getattr(verdict, "est_completion_date", "") or ""
    states = getattr(verdict, "states", []) or []
    reasons = getattr(verdict, "reasons", []) or []

    facility_name = entry_title or ""
    location = ", ".join(states)
    scale = f"{scale_value} {scale_unit}".strip() if scale_value is not None else ""

    if est_buy_window:
        next_action = f"WATCH: re-check near buy-window {est_buy_window}"
    else:
        next_action = "REVIEW: size & locate"

    row = {k: "" for k in DEMAND_HEADER}
    row.update({
        "demand_id": demand_id_for(source, segment, facility_name, location),
        "status": "reviewing",
        "segment": segment,
        "facility_name": facility_name,
        "owner_operator": "",
        "location": location,
        "scale": scale,
        "project_stage": project_stage,
        "est_buy_window": est_buy_window,
        "est_completion_date": est_completion_date,
        "signal_source": source or "",
        "source_url": source_url or "",
        "first_seen": today,
        "last_reviewed": today,
        "est_value": "",
        "next_action": next_action,
        "notes": "; ".join(reasons),
    })
    return row


def demand_match_keys(row: dict) -> set[str]:
    """Stable dedup keys recognizing the same demand signal across the Demand
    Radar review file and the archive.

    Reads demand_id plus signal_source/segment/facility_name/location. The
    derived key uses the same rule as build_demand_row, and the facility+location
    key catches the same facility re-surfaced from a different source.
    """
    keys: set[str] = set()
    facility = (row.get("facility_name") or "").strip()
    location = (row.get("location") or "").strip()

    explicit = (row.get("demand_id") or "").strip()
    if explicit:
        keys.add(f"demand:{explicit.lower()}")
    derived = demand_id_for(
        row.get("signal_source") or "", row.get("segment") or "",
        facility, location,
    )
    if derived and derived != "untitled":
        keys.add(f"demand:{derived.lower()}")
    keys.add(f"facloc:{facility.lower()}:{location.lower()}")
    return keys


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------
def _validate_date(value: str, field: str) -> None:
    if not value:
        return
    # est_completion_date may be a bare "YYYY" (a project that only names a year).
    if field == "est_completion_date" and _YEAR_RE.fullmatch(value):
        return
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{field}: expected YYYY-MM-DD, got {value!r} ({exc})") from exc


def _validate_buy_window(value: str) -> None:
    if not value:
        return
    try:
        datetime.strptime(value, "%Y-%m")
    except ValueError as exc:
        raise ValueError(f"est_buy_window: expected YYYY-MM, got {value!r} ({exc})") from exc


# ---------------------------------------------------------------------
# CSV helpers (Demand Radar header; mirrors pipeline.read_rows/write_rows_atomic)
# ---------------------------------------------------------------------
def read_demand_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (header, rows) for a Demand Radar CSV. Header must match DEMAND_HEADER."""
    if not path.exists():
        raise FileNotFoundError(f"demand radar file not found: {path}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header = list(reader.fieldnames or [])
        if header != DEMAND_HEADER:
            raise ValueError(
                f"{path}: header drifted from canonical.\n"
                f"  got:      {header}\n"
                f"  expected: {DEMAND_HEADER}"
            )
        rows = [{k: (row.get(k) or "") for k in DEMAND_HEADER} for row in reader]
    return header, rows


def write_demand_rows_atomic(path: Path, rows: Iterable[dict]) -> None:
    """Write CSV atomically: tmp file in same dir, then os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=DEMAND_HEADER, lineterminator="\n")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in DEMAND_HEADER})
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
def _buy_window_sort_key(row: dict) -> tuple:
    bw = row.get("est_buy_window") or ""
    return (1, "") if not bw else (0, bw)


def cmd_summary(args: argparse.Namespace) -> int:
    review = Path(args.review)
    _, rows = read_demand_rows(review)

    print(f"Demand Radar: {review}")
    print(f"Total signals: {len(rows)}")
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
    print_counter("segment", "segment")
    print_counter("project_stage", "project_stage")

    # Buy-windows in the next 180 days — the actionable horizon. A buy-window is
    # a YYYY-MM; treat it as the first of that month and include it when it falls
    # between the current month and ~180 days out. Sorted ascending; rows whose
    # window is blank or unparseable are listed last for visibility.
    today = datetime.now().date()
    cutoff = today + timedelta(days=180)
    month_start = today.replace(day=1)

    upcoming: list[tuple[str, dict]] = []
    blank: list[dict] = []
    for r in rows:
        bw = (r.get("est_buy_window") or "").strip()
        if not bw:
            blank.append(r)
            continue
        try:
            wd = datetime.strptime(bw, "%Y-%m").date()
        except ValueError:
            blank.append(r)
            continue
        if month_start <= wd <= cutoff:
            upcoming.append((bw, r))

    upcoming.sort(key=lambda kv: kv[0])
    print("Buy-windows in next 180 days:")
    if not upcoming:
        print("  (none)")
    else:
        for bw, r in upcoming:
            label = r.get("facility_name") or r.get("demand_id") or "(unnamed)"
            loc = r.get("location") or "?"
            print(f"  {bw}  {label}  [{r.get('segment') or '?'} | {loc}]")
    if blank:
        print(f"  (+{len(blank)} with no buy-window)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    review = Path(args.review)
    _, rows = read_demand_rows(review)

    if args.status:
        rows = [r for r in rows if (r.get("status") or "") == args.status]
    if args.segment:
        rows = [r for r in rows if (r.get("segment") or "") == args.segment]

    rows.sort(key=_buy_window_sort_key)

    if not rows:
        print(f"(no demand signals in {review})")
        return 0

    cols = ("demand_id", "status", "segment", "project_stage", "est_buy_window",
            "location", "facility_name")
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
    try:
        _validate_buy_window(args.est_buy_window or "")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.status and args.status not in STATUS_VALUES:
        print(f"error: status {args.status!r} not in {list(STATUS_VALUES)}", file=sys.stderr)
        return 1
    if args.segment and args.segment not in SEGMENT_VALUES:
        print(f"error: segment {args.segment!r} not in {list(SEGMENT_VALUES)}", file=sys.stderr)
        return 1
    if args.project_stage and args.project_stage not in STAGE_VALUES:
        print(f"error: project_stage {args.project_stage!r} not in {list(STAGE_VALUES)}", file=sys.stderr)
        return 1

    if not args.signal_source:
        print("error: --signal-source is required", file=sys.stderr)
        return 1
    if not (args.facility_name or args.location):
        print("error: one of --facility-name or --location is required to derive a demand_id",
              file=sys.stderr)
        return 1

    demand_id = args.demand_id or demand_id_for(
        args.signal_source, args.segment or "", args.facility_name or "", args.location or "",
    )

    review = Path(args.review)
    if not review.exists():
        write_demand_rows_atomic(review, [])
    _, rows = read_demand_rows(review)

    existing_idx = next((i for i, r in enumerate(rows) if r.get("demand_id") == demand_id), None)
    if existing_idx is not None and not args.overwrite:
        print(f"error: demand_id {demand_id!r} already exists. Pass --overwrite to replace.",
              file=sys.stderr)
        return 1

    today = datetime.now().date().isoformat()
    if args.est_buy_window:
        default_next = f"WATCH: re-check near buy-window {args.est_buy_window}"
    else:
        default_next = "REVIEW: size & locate"

    new_row = {k: "" for k in DEMAND_HEADER}
    new_row.update({
        "demand_id": demand_id,
        "status": args.status or "reviewing",
        "segment": args.segment or "",
        "facility_name": args.facility_name or "",
        "owner_operator": args.owner_operator or "",
        "location": args.location or "",
        "scale": args.scale or "",
        "project_stage": args.project_stage or "",
        "est_buy_window": args.est_buy_window or "",
        "est_completion_date": args.est_completion_date or "",
        "signal_source": args.signal_source,
        "source_url": args.source_url or "",
        "first_seen": args.first_seen or today,
        "last_reviewed": args.last_reviewed or today,
        "est_value": args.est_value or "",
        "next_action": args.next_action or default_next,
        "notes": args.notes or "",
    })

    if existing_idx is not None:
        rows[existing_idx] = new_row
        action = "replaced"
    else:
        rows.append(new_row)
        action = "added"

    write_demand_rows_atomic(review, rows)
    print(f"{action} {demand_id} in {review}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    review = Path(args.review)
    archive = Path(args.archive)
    _, rows = read_demand_rows(review)

    idx = next((i for i, r in enumerate(rows) if r.get("demand_id") == args.demand_id), None)
    if idx is None:
        print(f"error: demand_id {args.demand_id!r} not found in {review}", file=sys.stderr)
        return 1

    if args.status and args.status not in STATUS_VALUES:
        print(f"error: status {args.status!r} not in {list(STATUS_VALUES)}", file=sys.stderr)
        return 1

    moved_row = rows.pop(idx)
    # Default to the terminal 'archived' status unless the caller set a more
    # specific close reason (no-fit / stale / converted).
    moved_row["status"] = args.status or "archived"
    if args.next_action is not None:
        moved_row["next_action"] = args.next_action
    if args.note:
        existing = moved_row.get("notes") or ""
        moved_row["notes"] = f"{existing}; {args.note}" if existing else args.note
    moved_row["last_reviewed"] = datetime.now().date().isoformat()

    if not archive.exists():
        write_demand_rows_atomic(archive, [])
    _, archive_rows = read_demand_rows(archive)

    archive_idx = next((i for i, r in enumerate(archive_rows) if r.get("demand_id") == args.demand_id), None)
    if archive_idx is not None:
        archive_rows[archive_idx] = moved_row
    else:
        archive_rows.append(moved_row)

    # Write and verify the archive before removing the row from review, so a
    # failed second write never loses the signal.
    write_demand_rows_atomic(archive, archive_rows)
    _, verified = read_demand_rows(archive)
    if not any(r.get("demand_id") == args.demand_id for r in verified):
        print(f"error: archive write did not persist {args.demand_id!r}; review left unchanged",
              file=sys.stderr)
        return 1
    write_demand_rows_atomic(review, rows)
    print(f"archived {args.demand_id} from {review} to {archive} (status={moved_row['status']})")
    return 0


def cmd_outreach(args: argparse.Namespace) -> int:
    """Human handoff. A pre-RFP demand signal has no solicitation, so this never
    promotes to / touches the bid pipeline — only the Demand Radar review CSV is
    written. It records who was contacted and sets a dated follow-up."""
    review = Path(args.review)
    _, rows = read_demand_rows(review)

    idx = next((i for i, r in enumerate(rows) if r.get("demand_id") == args.demand_id), None)
    if idx is None:
        print(f"error: demand_id {args.demand_id!r} not found in {review}", file=sys.stderr)
        return 1

    row = rows[idx]
    today = datetime.now().date()
    row["status"] = "outreach"
    row["last_reviewed"] = today.isoformat()

    bits = [f"outreach contact: {args.contact}"]
    if args.note:
        bits.append(args.note)
    addition = "; ".join(bits)
    row["notes"] = f"{row.get('notes')}; {addition}" if row.get("notes") else addition

    follow_up = (today + timedelta(days=14)).isoformat()
    row["next_action"] = f"FOLLOW-UP by {follow_up}: re-contact {args.contact}"

    # NOTE: Demand Radar is parallel to the bid pipeline and writes ONLY the
    # review CSV here — nothing under bids/ is read or written.
    write_demand_rows_atomic(review, rows)
    print(f"outreach logged for {args.demand_id} (contact: {args.contact}); "
          f"next follow-up {follow_up}")
    return 0


# ---------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", default=str(DEFAULT_REVIEW), help="Demand Radar review CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Demand Radar archive CSV (default: %(default)s)")

    sub = parser.add_subparsers(dest="command", required=True)

    p_sum = sub.add_parser("summary", help="Counts by status/segment/stage + upcoming buy-windows.")
    p_sum.set_defaults(func=cmd_summary)

    p_list = sub.add_parser("list", help="Print demand rows (optionally filtered).")
    p_list.set_defaults(func=cmd_list)
    p_list.add_argument("--status", default="", help=f"Filter by status. One of {list(STATUS_VALUES)}.")
    p_list.add_argument("--segment", default="", help=f"Filter by segment. One of {list(SEGMENT_VALUES)}.")

    p_add = sub.add_parser("add", help="Append a new demand row.")
    p_add.set_defaults(func=cmd_add)
    p_add.add_argument("--demand-id", help="Explicit id; derived from source+segment+facility/location if omitted.")
    p_add.add_argument("--status", help=f"One of {list(STATUS_VALUES)} (default: reviewing)")
    p_add.add_argument("--segment", help=f"One of {list(SEGMENT_VALUES)}")
    p_add.add_argument("--facility-name", default="")
    p_add.add_argument("--owner-operator", default="")
    p_add.add_argument("--location", default="")
    p_add.add_argument("--scale", default="", help="Human-readable scale, e.g. '180 keys'.")
    p_add.add_argument("--project-stage", help=f"One of {list(STAGE_VALUES)}")
    p_add.add_argument("--est-buy-window", default="", help="YYYY-MM — the key actionable field.")
    p_add.add_argument("--est-completion-date", default="", help="YYYY-MM-DD or bare YYYY.")
    p_add.add_argument("--signal-source", required=True)
    p_add.add_argument("--source-url", default="")
    p_add.add_argument("--first-seen", default="")
    p_add.add_argument("--last-reviewed", default="")
    p_add.add_argument("--est-value", default="")
    p_add.add_argument("--next-action", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--overwrite", action="store_true", help="Replace an existing row with the same demand_id.")

    p_arc = sub.add_parser("archive", help="Move a demand row from review to the demand archive.")
    p_arc.set_defaults(func=cmd_archive)
    p_arc.add_argument("demand_id", help="Demand id to archive.")
    p_arc.add_argument("--status", default=None, help=f"Close status (default: archived). One of {list(STATUS_VALUES)}.")
    p_arc.add_argument("--next-action", default=None, help="Replace next_action on the archived row. Pass '' to clear.")
    p_arc.add_argument("--note", default=None, help="Append text to the notes column (separator '; ').")

    p_out = sub.add_parser(
        "outreach",
        help="Human handoff: mark a row 'outreach' and set a dated follow-up.",
    )
    p_out.set_defaults(func=cmd_outreach)
    p_out.add_argument("demand_id", help="Demand id to mark for outreach.")
    p_out.add_argument("--contact", required=True, help="Who was/should be contacted (developer / GC / FF&E firm / owner).")
    p_out.add_argument("--note", default="", help="Optional note appended to the notes column.")

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
