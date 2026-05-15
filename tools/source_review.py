#!/usr/bin/env python3
"""
source_review.py - generate an operator portal-review checklist.

Reads sources/procurement_sources.json, filters by cadence, excludes
sources that are already covered by automation (has_api: true, e.g.
SAM.gov), and writes a Markdown checklist to:

    build/portal_reviews/<date>_<cadence>.md

The generated file is gitignored. It is intended as a single-session
operator worksheet: walk each portal's UI / email-notification feed,
add anything worth pursuing to the pipeline via tools/pipeline.py add,
and discard the worksheet. Committed source of truth remains the
registry (sources/procurement_sources.json) and the pipeline CSVs.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "sources" / "procurement_sources.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "portal_reviews"

CADENCE_CHOICES = ("weekly", "monthly", "ad_hoc", "all")

REMINDER = (
    "**Operating rules:** Do not scrape portals. Use the official portal UI "
    "or email notifications you are already subscribed to. When you find an "
    "opportunity worth pursuing, record it with "
    "`python tools/pipeline.py add ...`. The completed worksheet stays local "
    "(build/ is gitignored); the registry and pipeline rows are the "
    "committed source of truth."
)


def load_registry(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def filter_sources(sources: list[dict], cadence: str) -> list[dict]:
    """Return non-API sources matching the cadence filter.

    Sources with has_api=True are always excluded - they are covered by
    automation (e.g. tools/ingest_sam.py + the scheduled GitHub Action).
    """
    non_api = [s for s in sources if not s.get("has_api")]
    if cadence == "all":
        return non_api
    return [s for s in non_api if s.get("cadence") == cadence]


def list_cadences(sources: list[dict]) -> list[str]:
    """Return sorted unique cadence values across non-API sources."""
    return sorted({s["cadence"] for s in sources if not s.get("has_api") and s.get("cadence")})


def _fmt_list(items: list[str] | None) -> str:
    if not items:
        return "(none)"
    return ", ".join(items)


def render_checklist(sources: list[dict], cadence: str, date: str) -> str:
    """Build the Markdown body (ASCII-only)."""
    lines: list[str] = []
    lines.append(f"# Portal review - {date} ({cadence} cadence)")
    lines.append("")
    lines.append(REMINDER)
    lines.append("")
    lines.append(f"Sources to review: {len(sources)}")
    lines.append("")

    # Scoreboard
    lines.append("## Scoreboard")
    lines.append("")
    lines.append("| # | Source | Buyer level | Reviewed? | Opportunities | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for i, s in enumerate(sources, 1):
        lines.append(f"| {i} | {s['name']} | {s.get('buyer_level','')} |  |  |  |")
    lines.append("")

    # Per-source details
    lines.append("## Per-source details")
    lines.append("")
    for s in sources:
        lines.append(f"### {s['name']}")
        lines.append("")
        url = s.get("official_url") or "(no URL on file)"
        lines.append(f"- URL: {url}")
        geography = _fmt_list(s.get("geography"))
        lines.append(f"- Buyer level: {s.get('buyer_level','')} ({geography})")
        lines.append(f"- Intake method: {s.get('intake_method','')}")
        lines.append(f"- Cadence: {s.get('cadence','')}")
        lines.append(f"- Search terms: {_fmt_list(s.get('search_terms'))}")
        lines.append(f"- Commodity terms: {_fmt_list(s.get('commodity_terms'))}")
        notes = (s.get("notes") or "").strip()
        if notes:
            lines.append(f"- Registry notes: {notes}")
        lines.append("")
        lines.append("Checklist:")
        lines.append("- [ ] Logged in / accessed portal")
        lines.append("- [ ] Ran saved search(es) for the search terms above")
        lines.append("- [ ] Reviewed new postings since last check")
        lines.append("- [ ] Added relevant opportunities via `python tools/pipeline.py add ...`")
        lines.append("- [ ] No relevant opportunities found this cycle")
        lines.append("")
        lines.append("Opportunity IDs added:")
        lines.append("-")
        lines.append("")
        lines.append("Operator notes:")
        lines.append("-")
        lines.append("")

    return "\n".join(lines) + "\n"


def _validate_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--date must be YYYY-MM-DD ({exc})"
        ) from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--cadence",
        choices=CADENCE_CHOICES,
        default="weekly",
        help="Which cadence bucket to review (default: %(default)s).",
    )
    parser.add_argument(
        "--date",
        type=_validate_date,
        default=None,
        help="Date stamp in the output (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_REGISTRY),
        help=f"Source registry JSON (default: {DEFAULT_REGISTRY.relative_to(REPO_ROOT)}).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Explicit output path. Defaults to "
            "build/portal_reviews/<date>_<cadence>.md (gitignored)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the checklist to stdout; do not write a file.",
    )
    parser.add_argument(
        "--list-cadences",
        action="store_true",
        help="Print the cadence values present in the registry (excluding API sources) and exit.",
    )
    args = parser.parse_args(argv)

    try:
        sources = load_registry(Path(args.registry))
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: registry is not valid JSON: {exc}", file=sys.stderr)
        return 1

    if args.list_cadences:
        for c in list_cadences(sources):
            print(c)
        return 0

    date_str = args.date or datetime.now().date().isoformat()
    filtered = filter_sources(sources, args.cadence)

    if not filtered:
        print(
            f"No non-API sources match cadence={args.cadence!r}; "
            f"nothing to review. No file written."
        )
        return 0

    body = render_checklist(filtered, args.cadence, date_str)

    if args.dry_run:
        sys.stdout.write(body)
        return 0

    output_path = (
        Path(args.output)
        if args.output
        else DEFAULT_OUTPUT_DIR / f"{date_str}_{args.cadence}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(body, encoding="utf-8")
    print(f"wrote {output_path}")
    print(f"  {len(filtered)} source(s), cadence={args.cadence}, date={date_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
