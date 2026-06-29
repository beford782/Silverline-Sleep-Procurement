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
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REVIEW = REPO_ROOT / "leads" / "review" / "_lead_radar.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "leads" / "archive" / "_lead_radar_archive.csv"
TEMPLATE_HEADER = REPO_ROOT / "templates" / "lead_radar_tracker.csv"

# Re-bid / contract-expiry calendar artifacts (written by the `calendar`
# subcommand). The event payloads are what an operator/assistant later pushes
# to Google Calendar; the idempotency ledger records which keys are already
# scheduled so a future apply step only creates new events.
DEFAULT_CALENDAR_EVENTS = REPO_ROOT / "leads" / "review" / "_calendar_events.json"
DEFAULT_CALENDAR_STATE = REPO_ROOT / "leads" / "review" / "_calendar_state.json"

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
# Re-bid / contract-expiry calendar
# ---------------------------------------------------------------------
# Turns dead "set a reminder ~6 mo prior" text in awarded_contract_watch notes
# into dated prep-windows: prep_window = expiry - lead_time, surfaced in the
# digest and emitted as a CI-safe event payload an operator/assistant can push
# to Google Calendar. This module is STDLIB-ONLY and never touches the network
# or any MCP tool — it only reads the Lead Radar CSV and reads/writes the local
# JSON ledger. Pushing events to a calendar is an OPERATOR/ASSISTANT step (see
# CALENDAR_HELP).

# Prep-window lead times by source class (days before contract expiry that prep
# should begin). Co-op / state-term vehicles need long runway (positioning,
# portal repair, buyer touches); recurring federal channels move faster.
CALENDAR_LEAD_TIME_COOP = 180
CALENDAR_LEAD_TIME_FEDERAL = 60
CALENDAR_LEAD_TIME_DEFAULT = 120

# Co-op / state-term vehicle markers (matched in source+buyer, lowercased).
_COOP_MARKERS = ("buyboard", "tips", "sourcewell", "omnia", "choice", "e&i")

# The prep ladder that becomes the event description (and a good next_action).
PREP_CHECKLIST = [
    "Confirm spec & expiry with buyer contact.",
    "Pull last award price + incumbent.",
    "Register/repair portal as the LLC (blank UEI if SAM unresolved).",
    "Buyer touch / get specified.",
    "Draft response; create active pipeline row at expiry-30d.",
]

CALENDAR_HELP = """\
calendar — surface awarded-contract re-bid windows as dated prep events.

Selects awarded_contract_watch leads (and recurring federal channel rows),
computes prep_window = expiry - lead_time, and writes CI-safe event payloads
to leads/review/_calendar_events.json (or stdout with --stdout). A text table
of upcoming prep windows is always printed (sorted by prep_window).

Lead times by source class:
  co-op / state-term (BuyBoard, TIPS, Sourcewell, OMNIA, Choice, E&I): 180 days
  SAM / federal recurring channel:                                      60 days
  default:                                                             120 days

Rows with a blank expiry emit a WARN line and create NO event. Prep windows
already in the past are still emitted, flagged OVERDUE, so nothing lapses.

NO NETWORK / NO MCP happens here (CI stays green/stdlib-only). Pushing events
to Google Calendar is an OPERATOR/ASSISTANT step:
  1. Read leads/review/_calendar_events.json.
  2. For each event with "already_scheduled": false, call the Google Calendar
     MCP tool mcp__claude_ai_Google_Calendar__create_event (all-day event on
     "start", using "title" and "description").
  3. Record the returned event id back into leads/review/_calendar_state.json
     under the event "key" so the next emit marks it already_scheduled.
"""


def parse_due(value: str) -> "date | None":
    """Parse an ISO YYYY-MM-DD expiry; return None for blank/unparseable."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_federal_recurring(row: dict) -> bool:
    """True for a recurring federal (SAM.gov) demand-channel row."""
    src = (row.get("source") or "").lower()
    soln = (row.get("solicitation_number") or "").lower()
    return ("sam.gov" in src or "federal" in src) and "recurring" in soln


def is_calendar_candidate(row: dict) -> bool:
    """Rows that belong on the re-bid calendar: awarded_contract_watch leads
    plus cleanly-identifiable recurring federal channels."""
    if (row.get("lead_type") or "") == "awarded_contract_watch":
        return True
    return is_federal_recurring(row)


def calendar_lead_time_days(row: dict) -> int:
    """Days before expiry that prep should begin, by source class."""
    if is_federal_recurring(row):
        return CALENDAR_LEAD_TIME_FEDERAL
    blob = ((row.get("source") or "") + " " + (row.get("buyer") or "")).lower()
    if "sam.gov" in blob or "federal" in blob:
        return CALENDAR_LEAD_TIME_FEDERAL
    if any(marker in blob for marker in _COOP_MARKERS):
        return CALENDAR_LEAD_TIME_COOP
    return CALENDAR_LEAD_TIME_DEFAULT


def _event_title(row: dict) -> str:
    buyer = (row.get("buyer") or "").strip()
    soln = (row.get("solicitation_number") or "").strip()
    title = (row.get("title") or "").strip()
    head = " ".join(p for p in (buyer, soln) if p)
    return f"[Re-bid prep] {head} — {title}".strip()


def _event_description(row: dict, expiry: "date", prep_window: "date", lead_time: int) -> str:
    lines = ["Re-bid / contract-expiry prep checklist:"]
    for i, step in enumerate(PREP_CHECKLIST, 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    portal = (row.get("portal_url") or "").strip()
    if portal:
        lines.append(f"Portal: {portal}")
    # win_factors / win_score are not part of the Lead Radar schema today, but
    # include them when present (forward-compat); fit_score is the live signal.
    win_score = (row.get("win_score") or "").strip()
    win_factors = (row.get("win_factors") or "").strip()
    fit_score = (row.get("fit_score") or "").strip()
    if win_score:
        lines.append(f"Win score: {win_score}")
    if win_factors:
        lines.append(f"Win factors: {win_factors}")
    if fit_score:
        lines.append(f"Fit score: {fit_score}")
    lines.append(f"Contract expiry: {expiry.isoformat()}")
    lines.append(f"Prep window opens (expiry - {lead_time}d): {prep_window.isoformat()}")
    return "\n".join(lines)


def build_event(row: dict, today: "date") -> dict:
    """Build a calendar event payload for a candidate row with a parseable
    expiry. Caller is responsible for filtering / setting already_scheduled."""
    expiry = parse_due(row.get("due_date", ""))
    if expiry is None:
        raise ValueError("build_event requires a parseable due_date")
    lead_time = calendar_lead_time_days(row)
    prep_window = expiry - timedelta(days=lead_time)
    lead_id = (row.get("lead_id") or "").strip()
    return {
        "key": f"{lead_id}:{expiry.isoformat()}",
        "lead_id": lead_id,
        "title": _event_title(row),
        "start": prep_window.isoformat(),
        "all_day": True,
        "expiry": expiry.isoformat(),
        "lead_time_days": lead_time,
        "overdue": prep_window < today,
        "source": (row.get("source") or "").strip(),
        "buyer": (row.get("buyer") or "").strip(),
        "solicitation_number": (row.get("solicitation_number") or "").strip(),
        "portal_url": (row.get("portal_url") or "").strip(),
        "next_action": PREP_CHECKLIST[0],
        "description": _event_description(row, expiry, prep_window, lead_time),
        "already_scheduled": False,
    }


def load_calendar_state(path: Path) -> dict:
    """Read the idempotency ledger (key -> {event_id, created}); {} if absent."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def build_calendar_payload(
    rows: Iterable[dict],
    today: "date",
    horizon_days: int,
    state: "dict | None" = None,
) -> dict:
    """Pure, deterministic: turn Lead Radar rows into a calendar payload.

    Selects calendar candidates, emits events for those whose prep_window is
    within now..now+horizon (and any already-passed prep window as OVERDUE),
    flags already_scheduled from the ledger, and collects WARN entries for rows
    with a blank/unparseable expiry. No network, no file I/O.
    """
    state = state or {}
    horizon_end = today + timedelta(days=horizon_days)
    events: list[dict] = []
    warnings: list[dict] = []

    for row in rows:
        if not is_calendar_candidate(row):
            continue
        expiry = parse_due(row.get("due_date", ""))
        if expiry is None:
            if is_federal_recurring(row):
                msg = "recurring federal channel — no fixed expiry; track via SAM saved search (no event)"
            else:
                msg = "expiry unknown — confirm via buyer (no event)"
            warnings.append({
                "lead_id": (row.get("lead_id") or "").strip(),
                "buyer": (row.get("buyer") or "").strip(),
                "solicitation_number": (row.get("solicitation_number") or "").strip(),
                "message": msg,
            })
            continue
        event = build_event(row, today)
        # Within horizon, OR already overdue (always surface lapses).
        prep_window = date.fromisoformat(event["start"])
        if prep_window > horizon_end:
            continue
        event["already_scheduled"] = event["key"] in state
        events.append(event)

    events.sort(key=lambda e: (e["start"], e["key"]))
    warnings.sort(key=lambda w: w["lead_id"])
    return {
        "generated": today.isoformat(),
        "horizon_days": horizon_days,
        "events": events,
        "warnings": warnings,
    }


def _print_calendar_table(payload: dict) -> None:
    events = payload["events"]
    warnings = payload["warnings"]
    print(
        f"Re-bid prep windows (as of {payload['generated']}, "
        f"horizon {payload['horizon_days']}d): {len(events)} event(s), "
        f"{len(warnings)} warning(s)"
    )
    if events:
        cols = ("PREP WINDOW", "STATUS", "EXPIRY", "LT", "BUYER", "SOLICITATION", "TITLE")
        def status(e: dict) -> str:
            if e["overdue"]:
                return "OVERDUE"
            return "scheduled" if e["already_scheduled"] else "new"
        def trunc(s: str, n: int) -> str:
            return s if len(s) <= n else s[: n - 1] + "…"
        table = [[
            e["start"], status(e), e["expiry"], str(e["lead_time_days"]),
            trunc(e["buyer"], 36), trunc(e["solicitation_number"], 18),
            trunc(e["title"], 44),
        ] for e in events]
        widths = [max(len(cols[i]), max((len(r[i]) for r in table), default=0)) for i in range(len(cols))]
        print("  ".join(cols[i].ljust(widths[i]) for i in range(len(cols))))
        print("  ".join("-" * widths[i] for i in range(len(cols))))
        for r in table:
            print("  ".join(r[i].ljust(widths[i]) for i in range(len(cols))))
    else:
        print("  (no prep windows in horizon)")
    for w in warnings:
        ref = w["lead_id"] or w.get("solicitation_number") or "(unknown)"
        print(f"WARN: {ref}: {w['message']}")


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


def cmd_calendar(args: argparse.Namespace) -> int:
    review = Path(args.review)
    _, rows = read_lead_rows(review)

    if args.today:
        try:
            today = datetime.strptime(args.today, "%Y-%m-%d").date()
        except ValueError as exc:
            print(f"error: --today expected YYYY-MM-DD, got {args.today!r} ({exc})", file=sys.stderr)
            return 1
    else:
        today = datetime.now().date()

    if args.horizon < 0:
        print("error: --horizon must be >= 0", file=sys.stderr)
        return 1

    state = load_calendar_state(Path(args.state))
    payload = build_calendar_payload(rows, today, args.horizon, state)

    _print_calendar_table(payload)

    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.stdout:
        print()
        print(text)
    else:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print()
        print(
            f"Wrote {len(payload['events'])} event(s), "
            f"{len(payload['warnings'])} warning(s) to {out}"
        )
        print("Operator/assistant: push 'already_scheduled: false' events to Google "
              "Calendar via MCP, then record ids in "
              f"{Path(args.state)} (see `calendar --help`).")
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

    p_cal = sub.add_parser(
        "calendar",
        help="Emit awarded-contract re-bid prep windows as dated calendar events.",
        description=CALENDAR_HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_cal.set_defaults(func=cmd_calendar)
    p_cal.add_argument("--emit", action="store_true", default=True,
                       help="Emit prep windows (default; CI-safe, no network/MCP).")
    p_cal.add_argument("--horizon", type=int, default=1825,
                       help="Only include prep windows within now..now+DAYS (default: %(default)s ≈ 5y). "
                            "Already-passed windows are always included as OVERDUE.")
    p_cal.add_argument("--stdout", action="store_true",
                       help="Print the event-payload JSON to stdout instead of writing --out.")
    p_cal.add_argument("--out", default=str(DEFAULT_CALENDAR_EVENTS),
                       help="Event-payload JSON path (default: %(default)s).")
    p_cal.add_argument("--state", default=str(DEFAULT_CALENDAR_STATE),
                       help="Idempotency ledger JSON (key -> event_id) (default: %(default)s).")
    p_cal.add_argument("--today", default="",
                       help="Override 'today' as YYYY-MM-DD (determinism/testing).")

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
