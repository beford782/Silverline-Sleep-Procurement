#!/usr/bin/env python3
"""pii_lint.py - block likely PII from entering the tracked data files.

The CI "leak check" only catches machine-specific paths. This adds a focused
scan for likely personally-identifiable info that must NOT accumulate in the
auto-ingested data files: US street addresses, EINs, and phone numbers. The
ingest tools deliberately drop contact details, but a bad parse or a hand-edit
could let one through; this is the backstop.

SCOPE (deliberately tight, documented because it matters):
  - The default target set is the highest-risk data files only: the pipeline,
    Lead Radar, and Demand Radar CSVs. It does NOT scan the whole repo.
  - The CI gate runs in --diff-base mode, which scans ONLY lines ADDED relative
    to the base branch. This is the crucial scoping: these CSVs already carry
    PUBLIC buyer content in their free-text research notes (county purchasing
    office phone numbers, solicitation titles like "26-A-002 Providence Park
    Street") that pattern-match phone/street but are not PII. Whole-file scanning
    would red-CI on that legitimate history forever. Scanning only added lines
    keeps the goal honest: block NEW PII from ENTERING the data files, without
    auditing pre-existing public content.

ALLOWLIST: the PUBLIC company UEI (XF73FG8CVMX1) is allowlisted. When an added
line legitimately contains a public buyer phone/address, allowlist that exact
literal with --allow (repeatable) so the reviewer's intent is explicit.

Exit 1 (and print each hit) when anything matches; exit 0 when clean.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

# The data files most at risk of accreting PII via ingest / hand-edits.
DEFAULT_TARGETS = [
    REPO_ROOT / "bids" / "active" / "_pipeline.csv",
    REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv",
    REPO_ROOT / "leads" / "review" / "_lead_radar.csv",
    REPO_ROOT / "leads" / "demand" / "_demand_radar.csv",
    REPO_ROOT / "leads" / "demand" / "_demand_radar_archive.csv",
]

# Public, non-PII identifiers that are safe to commit.
PUBLIC_ALLOWLIST = {"XF73FG8CVMX1"}

_STREET_SUFFIX = (
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Ln|Lane|Way|"
    r"Ct|Court|Pl|Place|Pkwy|Parkway|Hwy|Highway|Ter|Terrace|Cir|Circle)"
)
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # e.g. "1234 Maple Street", "12 North Main Ave"
    ("street-address",
     re.compile(rf"\b\d{{1,6}}\s+(?:[A-Z][a-z]+\s+){{1,3}}{_STREET_SUFFIX}\b")),
    # EIN: 2 digits, dash, 7 digits (anchored so it does not catch ISO dates).
    ("ein", re.compile(r"\b\d{2}-\d{7}\b")),
    # US phone: 123-456-7890 or 123.456.7890
    ("phone", re.compile(r"\b\d{3}[-.]\d{3}[-.]\d{4}\b")),
]


def scan_text(text: str, allow: set[str]) -> list[tuple[int, str, str]]:
    """Return (line_no, kind, match) hits, skipping allowlisted literals."""
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in PATTERNS:
            for m in pattern.finditer(line):
                token = m.group(0)
                if token in allow:
                    continue
                hits.append((lineno, kind, token))
    return hits


def scan_file(path: Path, allow: set[str]) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return []
    return scan_text(text, allow)


def _added_lines(diff_base: str, targets: list[Path]) -> list[str]:
    """Return lines ADDED (relative to diff_base) across the target files."""
    rel = [str(p) for p in targets]
    cmd = ["git", "diff", "--unified=0", f"{diff_base}...HEAD", "--"] + rel
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
    except (OSError, ValueError):
        return []
    added: list[str] = []
    for line in out.splitlines():
        # Added content lines start with a single '+' (skip the '+++' file header).
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    return added


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*",
                        help="Files to scan (default: the pipeline + radar data CSVs).")
    parser.add_argument("--allow", action="append", default=[],
                        help="Additional public literal to allowlist (repeatable).")
    parser.add_argument("--diff-base", default=None,
                        help="Scan only lines ADDED relative to this git ref "
                             "(e.g. origin/main) instead of whole files. This is the "
                             "CI gate mode: it blocks NEW PII without tripping on the "
                             "public buyer content already in the data files' history.")
    args = parser.parse_args(argv)

    allow = set(PUBLIC_ALLOWLIST) | set(args.allow)
    targets = [Path(p) for p in args.paths] if args.paths else list(DEFAULT_TARGETS)

    total = 0
    if args.diff_base:
        for line in _added_lines(args.diff_base, targets):
            for _lineno, kind, token in scan_text(line, allow):
                total += 1
                print(f"::error::PII ({kind}) in added line: {token!r} :: {line.strip()[:120]}")
        if total:
            print(f"pii_lint: {total} likely-PII match(es) in newly added lines. "
                  f"Remove the PII, or allowlist a confirmed-public literal with --allow.")
            return 1
        print(f"pii_lint: OK (no PII in lines added vs {args.diff_base})")
        return 0

    for path in targets:
        if not path.exists():
            continue
        for lineno, kind, token in scan_file(path, allow):
            total += 1
            print(f"::error::PII ({kind}) in {path}:{lineno}: {token!r}")
    if total:
        print(f"pii_lint: {total} likely-PII match(es) found (whole-file mode). "
              f"Remove the PII or allowlist a confirmed-public literal with --allow.")
        return 1
    print(f"pii_lint: OK (scanned {len(targets)} target path(s), no PII found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
