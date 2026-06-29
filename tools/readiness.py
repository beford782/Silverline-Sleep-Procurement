#!/usr/bin/env python3
"""
readiness.py — the READINESS / ELIGIBILITY LEDGER.

The win_score answers "which winnable thing first?". But being *eligible to bid*
is often the real gate: a federal buy is dead while SAM is not Active, a Norix
brand-name spec is dead without a Norix authorization, a Vizient-routed buy is
dead unless we are a Vizient-eligible supplier. This module makes the pipeline's
gate columns LOAD-BEARING:

    compliance_blocker   "; "-joined list of the open eligibility blockers
    procurement_risk     "blocker" when any open blocker exists
    gate_status          "blocked" when blocked, else "bid_ready"

It reads the firm's capabilities from configs/capabilities.json (the same file
win_score reads for sam_active), detects each opportunity's eligibility
requirements from its text, and reports the subset NOT satisfied. The `backlog`
view groups open blockers across the whole pipeline + lead radar and ranks them
by the win_score they gate — so the operator sees "fix THIS to unlock the most
win-weighted pipeline" (SAM, which gates the recurring federal channels, is #1).

Stdlib only. Pure functions + an annotate/backlog/show CLI. CI-safe (no network).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

# Share win_score's structural-gate vocabulary (brand restrictions, federal
# channels) so the two modules never drift on what counts as brand-restricted or
# federal. readiness depends on win_score; win_score does NOT depend on readiness
# (no circular import).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import win_score  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_PATH = REPO_ROOT / "configs" / "capabilities.json"

# Current reality (mirrors configs/capabilities.json); used when the file is
# absent or malformed so a federal/brand buy stays gated rather than silently
# clearing.
DEFAULT_CAPS: dict = {
    "sam_active": False,
    "cfr_1633": True,
    "cal_tb_117": True,
    "fr_fluid_proof_covers": True,
    "gpo_eligibility": {
        "E&I": True, "DSSI": False, "Vizient": False,
        "Premier": False, "HealthTrust": False,
    },
    "bonding": False,
    "brand_authorizations": ["Restonic", "Spring Air"],
}

# Closed / terminal rows are not "open" pipeline — they cannot be unlocked, so
# they never count toward the backlog. Union of the pipeline and lead trackers'
# closing statuses.
CLOSED_STATUSES = {
    "awarded", "lost", "no-bid", "cancelled",      # pipeline
    "archived", "no-fit", "stale", "promoted",      # lead radar
}

# Brand-name / sole-source restriction (reused from win_score). A spec that
# names one of these brands requires an authorization for that brand.
BRAND_RESTRICT_RE = win_score.BRAND_RESTRICT_RE
FEDERAL_RE = win_score.FEDERAL_RE

# Normalize a matched brand token to a stable display name.
_BRAND_DISPLAY = {
    "norix": "Norix", "purple": "Purple", "tempur": "Tempur",
    "sealy": "Sealy", "sertabrand": "Serta", "hillrom": "Hill-Rom",
    "stryker": "Stryker",
}

# GPO / co-op vehicles whose mention implies the buy is routed through that
# vehicle (so we must be eligible under it). Keys match gpo_eligibility.
_GPO_PATTERNS = [
    ("Vizient", re.compile(r"(?<![A-Za-z])vizient(?![A-Za-z])", re.I)),
    ("Premier", re.compile(r"(?<![A-Za-z])premier(?![A-Za-z])", re.I)),
    ("DSSI", re.compile(r"(?<![A-Za-z])dssi(?![A-Za-z])", re.I)),
    ("E&I", re.compile(r"(?<![A-Za-z])e\s*&\s*i(?![A-Za-z])", re.I)),
    ("HealthTrust", re.compile(r"(?<![A-Za-z])health\s*trust(?![A-Za-z])", re.I)),
]

# Bonding language — a solicitation that requires a payment/performance bond.
BONDING_RE = re.compile(
    r"(?<![A-Za-z])(payment bond|performance bond|bid bond|bond required|"
    r"bonding required|surety bond)(?![A-Za-z])",
    re.I,
)

# Fire-retardant / flammability spec families. 16 CFR 1633 (open-flame) and the
# generic FR wording map to cfr_1633; California TB 117 maps to cal_tb_117.
CFR_1633_RE = re.compile(
    r"(?<![A-Za-z0-9])(16\s*cfr\s*1633|cfr\s*1633|fire[\s\-]?retardant|"
    r"flame[\s\-]?retardant|flammability)(?![A-Za-z0-9])",
    re.I,
)
TB_117_RE = re.compile(
    r"(?<![A-Za-z0-9])(cal(?:ifornia)?\.?\s*tb\s*117|tb[\s\-]?117|"
    r"technical bulletin 117)(?![A-Za-z0-9])",
    re.I,
)


@dataclass(frozen=True)
class Requirement:
    """One detected eligibility requirement for an opportunity.

    label   — human description of what the opportunity requires.
    cap_key — which capability gates it: "sam_active" / "brand" / "gpo" /
              "bonding" / "cfr_1633" / "cal_tb_117".
    detail  — brand or GPO name (for the brand/gpo cap_keys).
    blocker — the message emitted when the requirement is NOT met.
    """

    label: str
    cap_key: str
    detail: str
    blocker: str


# ---------------------------------------------------------------------
# Capabilities
# ---------------------------------------------------------------------
def load_capabilities(path: "str | Path" = CAPABILITIES_PATH) -> dict:
    """Load configs/capabilities.json over the DEFAULT_CAPS baseline.

    Robust: a missing or malformed file falls back to DEFAULT_CAPS so a federal
    or brand-restricted buy stays gated (never silently cleared)."""
    caps = dict(DEFAULT_CAPS)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            caps.update(data)
    except (OSError, ValueError):
        pass
    return caps


# ---------------------------------------------------------------------
# Requirement detection (pure text -> requirements; caps-independent)
# ---------------------------------------------------------------------
def _req_text(row: dict) -> str:
    """Eligibility-signal blob. Reads title/notes/spec_summary/source/
    trigger_terms plus the pipeline's product/commodity fields and buyer."""
    return " ".join(
        row.get(f, "") or ""
        for f in (
            "title", "notes", "spec_summary", "primary_products",
            "commodity_terms", "trigger_terms", "source", "buyer",
        )
    ).strip()


def _federal_text(row: dict) -> str:
    """Federal detection mirrors win_score: matched on source + buyer."""
    return ((row.get("source", "") or "") + " " + (row.get("buyer", "") or "")).strip()


def _norm_brand(raw: str) -> str:
    key = re.sub(r"[^a-z]", "", raw.lower())
    return _BRAND_DISPLAY.get(key, raw.strip().title())


def _matched_brands(text: str) -> list[str]:
    """Distinct brand display names named in the text, in first-seen order."""
    out: list[str] = []
    for m in BRAND_RESTRICT_RE.finditer(text or ""):
        name = _norm_brand(m.group(1))
        if name not in out:
            out.append(name)
    return out


def _matched_gpos(text: str) -> list[str]:
    return [name for name, rx in _GPO_PATTERNS if rx.search(text or "")]


def _detect(row: dict) -> list[Requirement]:
    """All eligibility requirements detected for an opportunity (no caps)."""
    text = _req_text(row)
    reqs: list[Requirement] = []

    if FEDERAL_RE.search(_federal_text(row)):
        reqs.append(Requirement("SAM Active (federal)", "sam_active", "",
                                "SAM not Active"))

    for brand in _matched_brands(text):
        reqs.append(Requirement(
            f"brand authorization: {brand}", "brand", brand,
            f"brand: {brand} not authorized"))

    if BONDING_RE.search(text):
        reqs.append(Requirement("bonding", "bonding", "",
                                "bonding required (not bonded)"))

    for gpo in _matched_gpos(text):
        reqs.append(Requirement(
            f"GPO eligibility: {gpo}", "gpo", gpo,
            f"GPO: {gpo} not eligible"))

    if CFR_1633_RE.search(text):
        reqs.append(Requirement("16 CFR 1633 (fire-retardant)", "cfr_1633", "",
                                "16 CFR 1633 cert not held"))
    if TB_117_RE.search(text):
        reqs.append(Requirement("CAL TB 117 (flammability)", "cal_tb_117", "",
                                "CAL TB 117 not met"))

    return reqs


def _is_met(req: Requirement, caps: dict) -> bool:
    if req.cap_key == "brand":
        authorized = {b.lower() for b in (caps.get("brand_authorizations") or [])}
        return req.detail.lower() in authorized
    if req.cap_key == "gpo":
        return bool((caps.get("gpo_eligibility") or {}).get(req.detail, False))
    return bool(caps.get(req.cap_key, False))


def requirements_for(row: dict) -> list[str]:
    """Human labels of every eligibility requirement detected for the row."""
    return [r.label for r in _detect(row)]


def blockers_for(row: dict, caps: dict) -> list[str]:
    """The subset of requirements NOT satisfied by caps (the open blockers)."""
    return [r.blocker for r in _detect(row) if not _is_met(r, caps)]


# ---------------------------------------------------------------------
# Annotate the pipeline gate columns
# ---------------------------------------------------------------------
def _today_iso(today) -> str:
    if isinstance(today, (date, datetime)):
        return today.isoformat() if isinstance(today, date) else today.date().isoformat()
    return str(today)


def annotate(rows: list[dict], caps: dict, today) -> list[tuple[dict, tuple, tuple]]:
    """Write the gate columns onto each row from its open blockers.

    Sets compliance_blocker / procurement_risk / gate_status (mirrors
    pipeline.cmd_score's in-place update). procurement_risk becomes "blocker"
    when blocked; a stale "blocker" is cleared when the blockers resolve, while
    an operator-set low/medium/high is preserved. Returns the list of changed
    rows as (row, old_triple, new_triple) for reporting; touches last_reviewed
    only on changed rows."""
    today_iso = _today_iso(today)
    updates: list[tuple[dict, tuple, tuple]] = []
    for row in rows:
        blockers = blockers_for(row, caps)
        new_blocker = "; ".join(blockers)
        new_gate = "blocked" if blockers else "bid_ready"
        cur_risk = row.get("procurement_risk") or ""
        if blockers:
            new_risk = "blocker"
        elif cur_risk == "blocker":
            new_risk = ""               # stale blocker resolved -> clear
        else:
            new_risk = cur_risk         # keep operator-set low/medium/high

        old = (row.get("compliance_blocker") or "", cur_risk, row.get("gate_status") or "")
        new = (new_blocker, new_risk, new_gate)
        if old != new:
            updates.append((row, old, new))
            row["last_reviewed"] = today_iso
        row["compliance_blocker"] = new_blocker
        row["procurement_risk"] = new_risk
        row["gate_status"] = new_gate
    return updates


# ---------------------------------------------------------------------
# Backlog: rank open blockers by the win_score they gate
# ---------------------------------------------------------------------
def _win_score_int(row: dict) -> int:
    raw = (row.get("win_score") or "").strip()
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        return 0


def _row_id(row: dict) -> str:
    return (row.get("opportunity_id") or row.get("lead_id")
            or row.get("title") or "(unknown)")


def _is_open(row: dict) -> bool:
    return (row.get("status") or "").strip().lower() not in CLOSED_STATUSES


def backlog(pipeline_rows: list[dict], lead_rows: list[dict],
            caps: dict) -> list[tuple[str, int, int, list[str]]]:
    """Group open blockers across all OPEN rows and rank by gated win_score.

    Returns (blocker, total_win_score, count, example_ids) sorted by
    total_win_score desc, then count desc, then blocker name (deterministic).
    example_ids holds up to three row ids per blocker. This surfaces SAM #1
    because it gates the recurring federal channels' win_score."""
    groups: dict[str, list] = {}
    for row in list(pipeline_rows) + list(lead_rows):
        if not _is_open(row):
            continue
        blockers = blockers_for(row, caps)
        if not blockers:
            continue
        ws = _win_score_int(row)
        rid = _row_id(row)
        for b in blockers:
            g = groups.setdefault(b, [0, 0, []])
            g[0] += ws
            g[1] += 1
            if len(g[2]) < 3:
                g[2].append(rid)
    result = [(b, g[0], g[1], g[2]) for b, g in groups.items()]
    result.sort(key=lambda t: (-t[1], -t[2], t[0]))
    return result


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------
def _load_pipeline_rows() -> "tuple[Path, list[dict]]":
    import pipeline  # noqa: E402
    path = pipeline.DEFAULT_ACTIVE
    if not path.exists():
        return path, []
    return path, pipeline.read_rows(path)[1]


def _load_lead_rows() -> list[dict]:
    import lead_radar  # noqa: E402
    path = lead_radar.DEFAULT_REVIEW
    if not path.exists():
        return []
    return lead_radar.read_lead_rows(path)[1]


def cmd_annotate(args: argparse.Namespace) -> int:
    import pipeline  # noqa: E402
    active = Path(args.active)
    if not active.exists():
        print(f"error: pipeline file not found: {active}", file=sys.stderr)
        return 1
    _, rows = pipeline.read_rows(active)
    caps = load_capabilities(args.capabilities)
    today = args.today or date.today()

    updates = annotate(rows, caps, today)
    if not updates:
        print("readiness: no changes (gate columns already in sync).")
        return 0

    print(f"readiness: {len(updates)} row(s) would change:")
    for row, _old, (blocker, risk, gate) in updates:
        shown = blocker if blocker else "(no blocker)"
        print(f"  {_row_id(row)}: gate_status={gate} procurement_risk={risk or '-'} "
              f"compliance_blocker={shown}")

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0

    pipeline.write_rows_atomic(active, rows)
    print(f"readiness: wrote {active}")
    return 0


def cmd_backlog(args: argparse.Namespace) -> int:
    caps = load_capabilities(args.capabilities)
    _, pipeline_rows = _load_pipeline_rows()
    lead_rows = _load_lead_rows()
    ranked = backlog(pipeline_rows, lead_rows, caps)

    print("Fix this to unlock the most win-weighted pipeline:")
    if not ranked:
        print("  (no open eligibility blockers — every open row is bid-ready)")
        return 0

    rows_out = [
        {
            "rank": str(i),
            "win": str(total),
            "rows": str(count),
            "blocker": blocker,
            "examples": ", ".join(ids),
        }
        for i, (blocker, total, count, ids) in enumerate(ranked, 1)
    ]
    cols = ("rank", "win", "rows", "blocker", "examples")
    widths = {c: max(len(c), max((len(r[c]) for r in rows_out), default=0)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows_out:
        print("  ".join(r[c].ljust(widths[c]) for c in cols))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    caps = load_capabilities(args.capabilities)
    _, pipeline_rows = _load_pipeline_rows()
    lead_rows = _load_lead_rows()
    target = args.row_id
    row = next(
        (r for r in list(pipeline_rows) + list(lead_rows) if _row_id(r) == target),
        None,
    )
    if row is None:
        print(f"error: row id {target!r} not found in pipeline or lead radar",
              file=sys.stderr)
        return 1

    reqs = _detect(row)
    print(f"row: {target}")
    print(f"title: {row.get('title') or '(none)'}")
    if not reqs:
        print("requirements: (none detected — no eligibility gate)")
        return 0
    print("requirements:")
    for r in reqs:
        status = "MET" if _is_met(r, caps) else "BLOCKED"
        suffix = "" if _is_met(r, caps) else f"  -> {r.blocker}"
        print(f"  [{status:7}] {r.label}{suffix}")
    blockers = [r.blocker for r in reqs if not _is_met(r, caps)]
    print()
    if blockers:
        print(f"OPEN BLOCKERS ({len(blockers)}): " + "; ".join(blockers))
    else:
        print("OPEN BLOCKERS (0): bid-ready")
    return 0


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD ({exc})") from exc


def build_parser() -> argparse.ArgumentParser:
    import pipeline  # noqa: E402
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--capabilities", default=str(CAPABILITIES_PATH),
                        help="Capabilities JSON (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ann = sub.add_parser(
        "annotate",
        help="Write gate_status/procurement_risk/compliance_blocker onto the pipeline.")
    p_ann.set_defaults(func=cmd_annotate)
    p_ann.add_argument("--active", default=str(pipeline.DEFAULT_ACTIVE),
                       help="Active pipeline CSV (default: %(default)s)")
    p_ann.add_argument("--dry-run", action="store_true",
                       help="Show changes without writing.")
    p_ann.add_argument("--today", type=_parse_iso_date, default=None,
                       help="Date stamped into last_reviewed (default: today).")

    p_bk = sub.add_parser(
        "backlog",
        help="Rank open eligibility blockers by the win_score they gate.")
    p_bk.set_defaults(func=cmd_backlog)

    p_show = sub.add_parser(
        "show", help="Requirements vs blockers for one row id.")
    p_show.set_defaults(func=cmd_show)
    p_show.add_argument("row_id", help="opportunity_id / lead_id / title to inspect.")

    return parser


def main(argv: "list[str] | None" = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
