#!/usr/bin/env python3
"""
dashboard.py - print a read-only operator dashboard for active bids.

The dashboard is intentionally not a generated artifact. It reads the
active pipeline, checks a few local bid/draft paths, and prints the
things an operator should look at today: deadlines, ownership gaps,
stale reviews, scoring gaps, high-risk rows, and drafts ready to
promote.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ACTIVE_DIR = REPO_ROOT / "bids" / "active"
DEFAULT_DRAFT_DIR = REPO_ROOT / "build" / "drafts"
DEFAULT_DAYS = 14
DEFAULT_STALE_DAYS = 14
SHOW_CHOICES = ("all", "deadlines", "hygiene", "risk", "drafts", "summary")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import read_rows  # noqa: E402


def parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _label(row: dict) -> str:
    oid = row.get("opportunity_id") or "(missing id)"
    title = row.get("title") or row.get("solicitation_number") or "(untitled)"
    buyer = row.get("buyer") or "(buyer blank)"
    return f"{oid} :: {buyer} :: {title}"


def _owner_suffix(row: dict) -> str:
    owner = (row.get("owner") or "").strip()
    return f" [owner: {owner}]" if owner else " [owner missing]"


def _dated_items(rows: list[dict], field: str, today: date, days: int) -> list[str]:
    horizon = today + timedelta(days=days)
    items: list[tuple[date, str]] = []
    for row in rows:
        value = parse_date(row.get(field) or "")
        if value is None or value > horizon:
            continue
        delta = (value - today).days
        if delta < 0:
            prefix = f"OVERDUE {abs(delta)}d"
        elif delta == 0:
            prefix = "TODAY"
        else:
            prefix = f"+{delta}d"
        items.append((value, f"{prefix} {value.isoformat()} - {_label(row)}{_owner_suffix(row)}"))
    return [text for _, text in sorted(items, key=lambda item: (item[0], item[1]))]


def _missing_owner_or_action(rows: list[dict]) -> list[str]:
    out: list[str] = []
    for row in rows:
        missing: list[str] = []
        if not (row.get("owner") or "").strip():
            missing.append("owner")
        if not (row.get("next_action") or "").strip():
            missing.append("next_action")
        if missing:
            out.append(f"{', '.join(missing)} - {_label(row)}")
    return sorted(out)


def _stale_reviews(rows: list[dict], today: date, stale_days: int) -> list[str]:
    out: list[tuple[int, str]] = []
    for row in rows:
        reviewed = parse_date(row.get("last_reviewed") or "")
        if reviewed is None:
            out.append((99999, f"missing last_reviewed - {_label(row)}"))
            continue
        age = (today - reviewed).days
        if age > stale_days:
            out.append((age, f"{age}d since review - {_label(row)}{_owner_suffix(row)}"))
    return [text for _, text in sorted(out, key=lambda item: (-item[0], item[1]))]


def _needs_scoring(rows: list[dict]) -> list[str]:
    out = []
    for row in rows:
        if not (row.get("fit_score") or "").strip() or not (row.get("risk_level") or "").strip():
            out.append(_label(row))
    return sorted(out)


def _high_risk(rows: list[dict]) -> list[str]:
    out = []
    for row in rows:
        product_risk = (row.get("risk_level") or "").strip().lower()
        procurement_risk = (row.get("procurement_risk") or "").strip().lower()
        if product_risk == "high" or procurement_risk in {"high", "blocker"}:
            fit = (row.get("fit_score") or "-").strip()
            blocker = (row.get("compliance_blocker") or "").strip()
            risk_bits = [f"product {product_risk or '-'}", f"procurement {procurement_risk or '-'}"]
            if blocker:
                risk_bits.append(f"blocker {blocker}")
            out.append(f"fit {fit}; {', '.join(risk_bits)} - {_label(row)}{_owner_suffix(row)}")
    return sorted(out)


def _drafts_ready(rows: list[dict], draft_dir: Path, active_dir: Path) -> list[str]:
    out = []
    for row in rows:
        oid = (row.get("opportunity_id") or "").strip()
        if not oid:
            continue
        draft_path = draft_dir / f"{oid}_draft.md"
        active_path = active_dir / f"{oid}.md"
        if draft_path.exists() and not active_path.exists():
            out.append(f"{oid} - promote with: python tools/promote_draft.py {oid}")
    return sorted(out)


def _win_score_int(row: dict) -> int | None:
    raw = (row.get("win_score") or "").strip()
    try:
        return int(raw)
    except ValueError:
        return None


def _top_win_score(rows: list[dict], limit: int) -> list[str]:
    """Best opportunities by win_score (desc), due_date asc tiebreak. Rows with
    no win_score yet are listed after scored ones."""
    def key(row: dict) -> tuple:
        ws = _win_score_int(row)
        ws_key = (1, 0) if ws is None else (0, -ws)
        due = row.get("due_date") or ""
        due_key = (1, "") if not due else (0, due)
        return (ws_key, due_key, _label(row))

    out = []
    for row in sorted(rows, key=key)[:limit]:
        ws = _win_score_int(row)
        due = row.get("due_date") or "no-due"
        out.append(f"win {ws if ws is not None else '-'}; due {due} - {_label(row)}{_owner_suffix(row)}")
    return out


def _counter_lines(rows: list[dict], key: str) -> list[str]:
    counter = Counter((row.get(key) or "(blank)") for row in rows)
    if not counter:
        return ["(none)"]
    return [f"{value}: {count}" for value, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))]


def _section(title: str, lines: list[str]) -> str:
    body = lines if lines else ["(none)"]
    return "\n".join([title, "-" * len(title), *body])


def render_dashboard(
    rows: list[dict],
    today: date,
    days: int,
    stale_days: int,
    draft_dir: Path,
    active_dir: Path,
    show: str,
) -> str:
    sections: list[str] = [f"Pipeline dashboard - {today.isoformat()}"]

    if show in ("all", "summary"):
        scored = [r for r in rows if _win_score_int(r) is not None]
        top = max((_win_score_int(r) for r in scored), default=None)
        summary = [f"active rows: {len(rows)}"]
        summary.append(f"win_score: {len(scored)} scored"
                       + (f", top {top}" if top is not None else ""))
        summary.append("")
        summary.append("Top opportunities by win_score:")
        summary.extend(_top_win_score(rows, 10) or ["(none)"])
        summary.append("")
        summary.append("By status:")
        summary.extend(_counter_lines(rows, "status"))
        summary.append("")
        summary.append("By risk_level:")
        summary.extend(_counter_lines(rows, "risk_level"))
        summary.append("")
        summary.append("By procurement_risk:")
        summary.extend(_counter_lines(rows, "procurement_risk"))
        summary.append("")
        summary.append("By gate_status:")
        summary.extend(_counter_lines(rows, "gate_status"))
        summary.append("")
        summary.append("By source:")
        summary.extend(_counter_lines(rows, "source"))
        sections.append(_section("Summary", summary))

    if show in ("all", "deadlines"):
        sections.append(_section(f"Response deadlines within {days}d", _dated_items(rows, "due_date", today, days)))
        sections.append(_section(f"Q&A deadlines within {days}d", _dated_items(rows, "question_deadline", today, days)))

    if show in ("all", "drafts"):
        sections.append(_section("Drafts ready to promote", _drafts_ready(rows, draft_dir, active_dir)))

    if show in ("all", "hygiene"):
        sections.append(_section("Missing owner or next action", _missing_owner_or_action(rows)))
        sections.append(_section(f"Stale reviews over {stale_days}d", _stale_reviews(rows, today, stale_days)))

    if show in ("all", "risk"):
        sections.append(_section("Needs scoring", _needs_scoring(rows)))
        sections.append(_section("High risk", _high_risk(rows)))

    return "\n\n".join(sections).rstrip() + "\n"


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD ({exc})") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--active-dir", default=str(DEFAULT_ACTIVE_DIR), help="Active bid markdown directory")
    parser.add_argument("--draft-dir", default=str(DEFAULT_DRAFT_DIR), help="Generated draft directory")
    parser.add_argument("--today", type=_parse_iso_date, default=None, help="Date for dashboard checks (default: today)")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Deadline horizon in days (default: %(default)s)")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS, help="Review age threshold in days")
    parser.add_argument("--show", choices=SHOW_CHOICES, default="all", help="Dashboard section to show")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.days < 0:
        print("error: --days must be >= 0", file=sys.stderr)
        return 2
    if args.stale_days < 0:
        print("error: --stale-days must be >= 0", file=sys.stderr)
        return 2
    try:
        _, rows = read_rows(Path(args.active))
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(
        render_dashboard(
            rows=rows,
            today=args.today or date.today(),
            days=args.days,
            stale_days=args.stale_days,
            draft_dir=Path(args.draft_dir),
            active_dir=Path(args.active_dir),
            show=args.show,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
