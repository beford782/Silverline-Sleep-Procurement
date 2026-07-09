#!/usr/bin/env python3
"""qa_check.py — run the whole pre-commit audit gate with one command.

Mirrors the CI job (.github/workflows/ci.yml) locally, in order:

  1. byte-compile tools/ and tests/
  2. every git-tracked *.json parses
  3. full unittest suite
  4. vendor-profile validator
  5. workflow drift check (add --fail-on-warnings to make warnings fatal)
  6. machine-path leak scan over tracked py/md/json/csv files
     (the pattern is read from ci.yml at runtime so it never appears
      verbatim in a file the scan itself covers)
  7. PII lint, diff-scoped against origin/main when available

Usage:
    python tools/qa_check.py                     # the standard gate
    python tools/qa_check.py --fail-on-warnings  # workflow warnings fatal too

Exit code 0 = gate passed. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LEAK_EXTS = {".py", ".md", ".json", ".csv"}

RESULTS: "list[tuple[str, bool, str]]" = []


def run(name: str, cmd: "list[str]") -> bool:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        cmd, cwd=REPO_ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    ok = proc.returncode == 0
    detail = "" if ok else (proc.stdout + proc.stderr).strip()[-2000:]
    RESULTS.append((name, ok, detail))
    print(("PASS" if ok else "FAIL") + f"  {name}")
    if not ok and detail:
        print("      " + "\n      ".join(detail.splitlines()[-15:]))
    return ok


def tracked_files() -> "list[str]":
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT,
        capture_output=True, text=True, encoding="utf-8",
    )
    return [line for line in out.stdout.splitlines() if line]


def leak_pattern_from_ci() -> "re.Pattern | None":
    """Extract the machine-path grep pattern from ci.yml (-E '<pattern>')."""
    text = CI_YML.read_text(encoding="utf-8")
    match = re.search(r"-E\s+'([^']+)'", text)
    if not match:
        return None
    # The ci.yml pattern is for grep -E over literal text; backslashes in it
    # are already escaped for the shell/grep, which re also accepts.
    return re.compile(match.group(1))


def check_leaks() -> bool:
    pattern = leak_pattern_from_ci()
    if pattern is None:
        RESULTS.append(("machine-path leak scan", False, "pattern not found in ci.yml"))
        print("FAIL  machine-path leak scan (could not extract pattern from ci.yml)")
        return False
    hits: "list[str]" = []
    for rel in tracked_files():
        path = REPO_ROOT / rel
        if path.suffix.lower() not in LEAK_EXTS or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(content.splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{rel}:{lineno}")
    ok = not hits
    RESULTS.append(("machine-path leak scan", ok, "; ".join(hits[:10])))
    print(("PASS" if ok else "FAIL") + "  machine-path leak scan")
    if hits:
        for h in hits[:10]:
            print(f"      leak: {h}")
    return ok


def origin_main_exists() -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "origin/main"],
        cwd=REPO_ROOT, capture_output=True,
    ).returncode == 0


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fail-on-warnings", action="store_true",
                        help="pass through to workflow_check.py")
    args = parser.parse_args(argv)
    py = sys.executable

    run("byte-compile tools/ tests/", [py, "-m", "compileall", "-q", "tools", "tests"])

    json_ok = True
    for rel in tracked_files():
        if rel.lower().endswith(".json"):
            if subprocess.run(
                [py, "-m", "json.tool", rel], cwd=REPO_ROOT, capture_output=True,
            ).returncode != 0:
                RESULTS.append((f"json parse: {rel}", False, ""))
                print(f"FAIL  json parse: {rel}")
                json_ok = False
    if json_ok:
        RESULTS.append(("all tracked JSON parses", True, ""))
        print("PASS  all tracked JSON parses")

    run("unit tests", [py, "-m", "unittest", "discover", "-s", "tests"])
    run("vendor profile validator",
        [py, "tools/validate_vendor_profile.py",
         "vendor-profiles/continental_silverline.profile.json"])

    wf_cmd = [py, "tools/workflow_check.py"]
    if args.fail_on_warnings:
        wf_cmd.append("--fail-on-warnings")
    run("workflow drift check", wf_cmd)

    check_leaks()

    if origin_main_exists():
        run("pii lint (diff vs origin/main)",
            [py, "tools/pii_lint.py", "--diff-base", "origin/main"])
    else:
        RESULTS.append(("pii lint", True, "skipped: no origin/main ref"))
        print("SKIP  pii lint (no origin/main ref)")

    failed = [name for name, ok, _ in RESULTS if not ok]
    print()
    if failed:
        print(f"qa_check: FAILED ({len(failed)}): " + "; ".join(failed))
        return 1
    print(f"qa_check: OK — {len(RESULTS)} check(s) passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
