#!/usr/bin/env python3
"""
workflow_check.py - check pipeline / bid markdown workflow drift.

This is an operator-facing guardrail. It reads the active and archive
pipeline CSVs, compares them with bid markdown files, and reports drift
that tends to create confusion during bid/no-bid work.

Hard errors fail the command. Warnings report hygiene items such as
missing owners, due dates, stale reviews, or missing optional archive
narratives. Use --fail-on-warnings when you want warnings to fail too.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"
DEFAULT_ACTIVE_DIR = REPO_ROOT / "bids" / "active"
DEFAULT_ARCHIVE_DIR = REPO_ROOT / "bids" / "archive"
DEFAULT_LEADS = REPO_ROOT / "leads" / "review" / "_lead_radar.csv"
DEFAULT_DEMAND = REPO_ROOT / "leads" / "demand" / "_demand_radar.csv"

OPEN_STATUSES = {"watching", "drafting", "submitted"}
CLOSED_STATUSES = {"awarded", "lost", "no-bid", "cancelled"}
STATUS_RE = re.compile(r"^\|\s*Status\s*\|\s*([^|]+?)\s*\|", re.IGNORECASE | re.MULTILINE)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import read_rows  # noqa: E402


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


def _bid_markdown_files(path: Path) -> dict[str, Path]:
    if not path.exists():
        return {}
    out: dict[str, Path] = {}
    for candidate in sorted(path.glob("*.md")):
        if candidate.name.startswith("_"):
            continue
        out[candidate.stem] = candidate
    return out


def _markdown_status(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = STATUS_RE.search(text)
    if not match:
        return ""
    return match.group(1).strip().lower()


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _row_label(row: dict) -> str:
    oid = row.get("opportunity_id") or "(missing id)"
    title = row.get("title") or row.get("solicitation_number") or "(untitled)"
    return f"{oid} :: {title}"


def _append_duplicate_id_findings(rows: list[dict], scope: str, findings: list[Finding]) -> None:
    seen: set[str] = set()
    dupes: set[str] = set()
    for row in rows:
        oid = (row.get("opportunity_id") or "").strip()
        if not oid:
            findings.append(Finding("ERROR", "missing-id", f"{scope} row is missing opportunity_id"))
            continue
        if oid in seen:
            dupes.add(oid)
        seen.add(oid)
    for oid in sorted(dupes):
        findings.append(Finding("ERROR", "duplicate-id", f"{scope} has duplicate opportunity_id {oid!r}"))


def _read_csv_rows(path: Path) -> list[dict]:
    """Generic CSV read (header-agnostic) for the lead/demand radars.

    Unlike pipeline.read_rows this does not enforce a canonical header, so the
    data-integrity checks can run over the Lead Radar / Demand Radar CSVs
    without coupling workflow_check to those schemas.
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _check_data_integrity(
    rows: list[dict],
    scope: str,
    today: date,
    findings: list[Finding],
    *,
    id_field: str,
    title_field: str | None = "title",
    no_future_date_fields: tuple[str, ...] = (),
    posted_field: str | None = None,
    due_field: str | None = None,
    score_fields: tuple[str, ...] = (),
) -> None:
    """Cheap CSV data-integrity checks (all WARN, so CI is never broken by data).

    - A date that should already have happened (posted/created/reviewed/seen)
      but lands in the FUTURE is almost always a typo or a bad parse.
    - posted_date AFTER due_date is an impossible ordering.
    - fit_score / win_score must sit in 0..100.
    These never fired before, so the audit's 6 future dates + 4 posted>due
    inversions slipped through silently. Deadlines (due_date, question_deadline,
    est_completion_date) are intentionally NOT future-checked — they belong in
    the future.
    """
    for row in rows:
        rid = (row.get(id_field) or "").strip() or "(missing id)"
        title = (row.get(title_field) or "").strip() if title_field else ""
        label = f"{rid} :: {title}" if title else rid

        for field in no_future_date_fields:
            d = _parse_date((row.get(field) or "").strip())
            if d and d > today:
                findings.append(Finding(
                    "WARN", "future-date",
                    f"{scope} {label}: {field}={row.get(field)!r} is in the future",
                ))

        if posted_field and due_field:
            posted = _parse_date((row.get(posted_field) or "").strip())
            due = _parse_date((row.get(due_field) or "").strip())
            if posted and due and posted > due:
                findings.append(Finding(
                    "WARN", "date-inversion",
                    f"{scope} {label}: {posted_field}={row.get(posted_field)} is after "
                    f"{due_field}={row.get(due_field)}",
                ))

        for field in score_fields:
            raw = (row.get(field) or "").strip()
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                findings.append(Finding(
                    "WARN", "score-not-numeric",
                    f"{scope} {label}: {field}={raw!r} is not numeric",
                ))
                continue
            if value < 0 or value > 100:
                findings.append(Finding(
                    "WARN", "score-out-of-range",
                    f"{scope} {label}: {field}={raw} is outside 0..100",
                ))

        if title_field and not title:
            findings.append(Finding(
                "WARN", "missing-required-field",
                f"{scope} {label}: missing required field {title_field!r}",
            ))


def _check_markdown_status(
    row: dict,
    md_path: Path,
    findings: list[Finding],
) -> None:
    md_status = _markdown_status(md_path)
    if not md_status:
        return
    csv_status = (row.get("status") or "").strip().lower()
    if csv_status and md_status != csv_status:
        findings.append(
            Finding(
                "ERROR",
                "status-mismatch",
                f"{md_path}: markdown status {md_status!r} does not match pipeline status {csv_status!r}",
            )
        )


def check_workflow(
    active_path: Path,
    archive_path: Path,
    active_dir: Path,
    archive_dir: Path,
    today: date,
    stale_days: int,
    require_active_markdown: bool = False,
    leads_path: Path | None = None,
    demand_path: Path | None = None,
) -> list[Finding]:
    _, active_rows = read_rows(active_path)
    _, archive_rows = read_rows(archive_path)
    active_md = _bid_markdown_files(active_dir)
    archive_md = _bid_markdown_files(archive_dir)
    active_by_id = {(r.get("opportunity_id") or "").strip(): r for r in active_rows}
    archive_by_id = {(r.get("opportunity_id") or "").strip(): r for r in archive_rows}
    findings: list[Finding] = []

    _append_duplicate_id_findings(active_rows, "active pipeline", findings)
    _append_duplicate_id_findings(archive_rows, "archive pipeline", findings)

    # Cheap CSV data-integrity checks across the pipeline + Lead/Demand radars.
    # All WARN: they surface bad data in the digest/log without breaking CI.
    for rows, scope in ((active_rows, "active pipeline"), (archive_rows, "archive pipeline")):
        _check_data_integrity(
            rows, scope, today, findings,
            id_field="opportunity_id", title_field="title",
            no_future_date_fields=("posted_date", "created_date", "last_reviewed"),
            posted_field="posted_date", due_field="due_date",
            score_fields=("fit_score", "win_score"),
        )
    if leads_path is not None:
        _check_data_integrity(
            _read_csv_rows(leads_path), "Lead Radar", today, findings,
            id_field="lead_id", title_field="title",
            no_future_date_fields=("posted_date", "created_date", "last_reviewed"),
            posted_field="posted_date", due_field="due_date",
            score_fields=("fit_score",),
        )
    if demand_path is not None:
        _check_data_integrity(
            _read_csv_rows(demand_path), "Demand Radar", today, findings,
            id_field="demand_id", title_field="facility_name",
            no_future_date_fields=("first_seen", "last_reviewed"),
        )

    for oid in sorted(set(active_by_id) & set(archive_by_id)):
        findings.append(Finding("ERROR", "active-archive-duplicate", f"{oid!r} appears in both active and archive"))

    for row in active_rows:
        oid = (row.get("opportunity_id") or "").strip()
        status = (row.get("status") or "").strip().lower()
        label = _row_label(row)
        if status in CLOSED_STATUSES:
            findings.append(Finding("ERROR", "closed-status-in-active", f"active row has closed status: {label} ({status})"))
        if oid in archive_md:
            findings.append(Finding("ERROR", "active-row-archived-md", f"active row has markdown in archive/: {oid}"))
        if oid not in active_md:
            if require_active_markdown or status in {"drafting", "submitted"}:
                findings.append(Finding("ERROR", "missing-active-md", f"active row is missing bids/active/{oid}.md: {label}"))
            elif status == "watching":
                findings.append(Finding("WARN", "missing-watch-md", f"watching row has no active markdown yet: {label}"))
        else:
            _check_markdown_status(row, active_md[oid], findings)

        # Eligibility gate (readiness.py owns these columns): a biddable row
        # (drafting/submitted) that still carries an OPEN eligibility blocker is
        # an error — we would be drafting/submitting something we are not
        # eligible to win. Fires only on the new gate columns, so rows that are
        # merely watching/no-bid are unaffected (backward-compatible).
        if status in {"drafting", "submitted"}:
            blocker = (row.get("compliance_blocker") or "").strip()
            proc_risk = (row.get("procurement_risk") or "").strip().lower()
            gate = (row.get("gate_status") or "").strip().lower()
            if blocker or proc_risk == "blocker" or gate == "blocked":
                reason = blocker or (proc_risk == "blocker" and "procurement_risk=blocker") \
                    or "gate_status=blocked"
                findings.append(Finding(
                    "ERROR",
                    "biddable-with-open-blocker",
                    f"biddable row ({status}) has an open eligibility blocker: "
                    f"{label} [{reason}]",
                ))

        if not (row.get("owner") or "").strip():
            findings.append(Finding("WARN", "missing-owner", f"active row has no owner: {label}"))
        if not (row.get("next_action") or "").strip():
            findings.append(Finding("WARN", "missing-next-action", f"active row has no next_action: {label}"))
        if not (row.get("due_date") or "").strip():
            findings.append(Finding("WARN", "missing-due-date", f"active row has no due_date: {label}"))
        reviewed = _parse_date((row.get("last_reviewed") or "").strip())
        if reviewed is None:
            findings.append(Finding("WARN", "missing-last-reviewed", f"active row has no valid last_reviewed: {label}"))
        elif (today - reviewed).days > stale_days:
            findings.append(
                Finding(
                    "WARN",
                    "stale-review",
                    f"active row last reviewed {(today - reviewed).days} days ago: {label}",
                )
            )

    for row in archive_rows:
        oid = (row.get("opportunity_id") or "").strip()
        status = (row.get("status") or "").strip().lower()
        label = _row_label(row)
        if status in OPEN_STATUSES:
            findings.append(Finding("ERROR", "open-status-in-archive", f"archive row has open status: {label} ({status})"))
        if oid in active_md:
            findings.append(Finding("ERROR", "archive-row-active-md", f"archive row still has markdown in active/: {oid}"))
        if oid in archive_md:
            _check_markdown_status(row, archive_md[oid], findings)
        elif status in {"awarded", "lost"}:
            findings.append(Finding("WARN", "missing-archive-md", f"closed row is missing archive markdown: {label}"))
        elif status == "no-bid" and f"{oid}_no_bid" not in archive_md:
            findings.append(Finding("WARN", "missing-no-bid-memo", f"no-bid row has no archive markdown or no-bid memo: {label}"))

    for stem, path in active_md.items():
        if stem not in active_by_id:
            findings.append(Finding("ERROR", "orphan-active-md", f"{path}: no matching active pipeline row"))
    for stem, path in archive_md.items():
        if stem.endswith("_no_bid"):
            stem = stem[:-7]
        if stem not in archive_by_id:
            findings.append(Finding("ERROR", "orphan-archive-md", f"{path}: no matching archive pipeline row"))

    return findings


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD ({exc})") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE), help="Archive pipeline CSV (default: %(default)s)")
    parser.add_argument("--active-dir", default=str(DEFAULT_ACTIVE_DIR), help="Active bid markdown directory")
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR), help="Archive bid markdown directory")
    parser.add_argument("--leads", default=str(DEFAULT_LEADS), help="Lead Radar CSV for data-integrity checks (default: %(default)s)")
    parser.add_argument("--demand", default=str(DEFAULT_DEMAND), help="Demand Radar CSV for data-integrity checks (default: %(default)s)")
    parser.add_argument("--today", type=_parse_iso_date, default=None, help="Date for stale-review checks (default: today)")
    parser.add_argument("--stale-days", type=int, default=14, help="Warn when active last_reviewed is older than this")
    parser.add_argument("--require-active-markdown", action="store_true", help="Treat every active row without markdown as an error")
    parser.add_argument("--fail-on-warnings", action="store_true", help="Exit non-zero when warnings are present")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stale_days < 0:
        print("error: --stale-days must be >= 0", file=sys.stderr)
        return 2
    try:
        findings = check_workflow(
            active_path=Path(args.active),
            archive_path=Path(args.archive),
            active_dir=Path(args.active_dir),
            archive_dir=Path(args.archive_dir),
            today=args.today or date.today(),
            stale_days=args.stale_days,
            require_active_markdown=args.require_active_markdown,
            leads_path=Path(args.leads),
            demand_path=Path(args.demand),
        )
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARN"]
    if not findings:
        print("workflow_check: OK (no findings)")
        return 0

    for finding in findings:
        print(f"{finding.severity}: {finding.code}: {finding.message}")
    print()
    print(f"workflow_check: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (args.fail_on_warnings and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
