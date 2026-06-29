#!/usr/bin/env python3
"""
win_score.py — the WIN SCORE: a composite 0..100 ranking of opportunities.

The pipeline's fit_score answers "is this our product?" (binary mattress fit).
The WIN SCORE answers the harder question an operator actually cares about:
"of the things that ARE our product, which should I work FIRST, and which are
un-winnable?" It folds four pure factors into one sortable number so the best
opportunities surface and un-winnable ones (brand-restricted, out-of-region,
blocked-federal, closed-incumbent, past-due) sink to the bottom.

    win_score = round(min(100, product_fit x value_tier x win_probability
                                x strategic_fit x 100))

  product_fit       0..1   relevance.classify confidence (the existing fit gate)
  value_tier        x      dollar size (bed-count backfill when value is blank)
  win_probability   x      in-region x structural barriers x incumbent vuln
  strategic_fit     x      home-region x core-segment x recurring multiplier

relevance.classify is the UNTOUCHED source of product fit — this module only
calls it and reads .confidence / .decision / .context / matched terms. The
federal/SAM gate reads configs/capabilities.json ("sam_active", default False).

Stdlib only. Pure functions + a `rank` CLI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# relevance.py is the single source of truth for product fit; import it the same
# way pipeline.py does whether we run as a script or are imported by a tool.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relevance  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES_PATH = REPO_ROOT / "configs" / "capabilities.json"

HOME_STATES = relevance.HOME_STATES_DEFAULT

# Brand-name / sole-source restrictions we cannot supply against. A spec that
# requires Norix/Purple/Tempur/etc. brand-name product is structurally
# un-winnable for us, so it is sunk hard (x0.05) rather than filtered (kept
# visible so the operator can confirm the restriction).
BRAND_RESTRICT_RE = re.compile(
    r"\b(norix|purple|tempur|sealy|serta brand|hill\W?rom|stryker)\b", re.I
)

UNIT_PRICE_DEFAULT = 120  # $/institutional mattress, used to backfill blank value
BEDCOUNT_RE = re.compile(
    r"\b(\d{2,5})\s*(beds?|mattress(?:es)?|bunks?|units?|twin\s*xl)\b", re.I
)

# Federal / SAM-gated channels: a federal buy is un-winnable while SAM is not
# active (see configs/capabilities.json). Matched on source + buyer.
FEDERAL_RE = re.compile(
    r"\b(sam\.gov|sam|federal|dla|gsa|sewp|micc|defense logistics|"
    r"dept\.? of defense|department of defense|u\.?s\.? army|air force|navy)\b",
    re.I,
)

# Recurring buying vehicles (awarded-contract watches, IDIQ/BPA/schedules) are
# strategically valuable even when not open today — you want to be ready for the
# rebid — so they get a recurring multiplier.
RECURRING_RE = re.compile(r"\b(idiq|bpa|schedule|sewp|gsa|recurring)\b", re.I)

# Core institutional segments (correctional + dorm/student-housing) are our
# best-fit, highest-margin lanes; reward them in strategic_fit.
CORE_CONTEXT = frozenset({
    "correctional", "detention", "jail", "jails", "prison", "prisons", "inmate",
    "dorm", "dormitory", "residence hall", "student housing",
})
CORE_LEAD_TYPES = frozenset({"correctional_detention", "dorm_student_housing"})


# ---------------------------------------------------------------------
# Text + value helpers (handle BOTH pipeline rows and lead rows)
# ---------------------------------------------------------------------
def _fit_text(row: dict) -> str:
    """Product-fit blob — mirrors pipeline.score_text plus lead trigger_terms.

    Pipeline rows carry title/primary_products/commodity_terms; lead rows carry
    title/trigger_terms. Build from whatever exists so classify() sees the same
    signal the pipeline scorer does."""
    return " ".join(
        row.get(f, "") or ""
        for f in ("title", "primary_products", "commodity_terms", "trigger_terms")
    ).strip()


def _geo_text(row: dict) -> str:
    """Wider blob for state detection — locations live in buyer/delivery/notes,
    not just the title."""
    return " ".join(
        row.get(f, "") or ""
        for f in ("title", "buyer", "delivery_location", "source",
                  "commodity_terms", "trigger_terms", "notes")
    ).strip()


def _brand_text(row: dict) -> str:
    """Per spec, brand restriction is read from title/notes/primary_products."""
    return " ".join(
        row.get(f, "") or "" for f in ("title", "notes", "primary_products")
    ).strip()


def _classify(row: dict) -> "relevance.Verdict":
    return relevance.classify(_fit_text(row))


def _parse_value(raw: str) -> float | None:
    """Parse an estimated_value cell to a float; blank/unparseable -> None."""
    cleaned = re.sub(r"[^\d.]", "", raw or "")
    if not cleaned or cleaned == ".":
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def _bedcount_value(text: str) -> float | None:
    """Largest bed/unit count in text x UNIT_PRICE_DEFAULT, or None."""
    counts = [int(m.group(1)) for m in BEDCOUNT_RE.finditer(text or "")]
    if not counts:
        return None
    return max(counts) * UNIT_PRICE_DEFAULT


def _bucket(v: float) -> float:
    if v < 25_000:
        return 0.5
    if v < 100_000:
        return 0.8
    if v <= 500_000:
        return 1.0
    return 1.2


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


_SAM_ACTIVE_CACHE: bool | None = None


def sam_active() -> bool:
    """Read sam_active from configs/capabilities.json. DEFAULT False when the
    file is absent or malformed (a federal buy stays gated until proven open)."""
    global _SAM_ACTIVE_CACHE
    if _SAM_ACTIVE_CACHE is not None:
        return _SAM_ACTIVE_CACHE
    active = False
    try:
        with CAPABILITIES_PATH.open("r", encoding="utf-8") as fh:
            active = bool(json.load(fh).get("sam_active", False))
    except (OSError, ValueError):
        active = False
    _SAM_ACTIVE_CACHE = active
    return active


# ---------------------------------------------------------------------
# The four factors (pure functions)
# ---------------------------------------------------------------------
def product_fit(row: dict) -> float:
    """relevance.classify confidence as 0..1."""
    return _classify(row).confidence / 100.0


def value_tier(row: dict) -> float:
    """Dollar-size multiplier. Blank value -> bed-count x $120 backfill ->
    re-bucket; blank with no bed-count -> neutral 0.7."""
    v = _parse_value(row.get("estimated_value", "") or "")
    if v is not None:
        return _bucket(v)
    backfill = _bedcount_value(_geo_text(row))
    if backfill is not None:
        return _bucket(backfill)
    return 0.7


def win_probability(row: dict, today: date) -> float:
    """How likely we are to actually win this — region x structural barriers x
    incumbent vulnerability. Starts at 1.0 and multiplies down."""
    p = 1.0

    # Region.
    states = relevance.detect_states(_geo_text(row))
    if states & HOME_STATES:
        p *= 1.0
    elif states:
        p *= 0.3          # detected, all out-of-region
    else:
        p *= 0.85         # no location named — unknown, mild discount

    # Structural HARD sinks.
    if BRAND_RESTRICT_RE.search(_brand_text(row)):
        p *= 0.05         # brand/sole-source restriction we cannot supply

    source = row.get("source", "") or ""
    buyer = row.get("buyer", "") or ""
    if FEDERAL_RE.search(source + " " + buyer) and not sam_active():
        p *= 0.0          # federal channel, SAM not active -> un-winnable

    due = _parse_date(row.get("due_date", "") or "")
    lead_type = row.get("lead_type", "") or ""
    if due is not None and due < today and lead_type != "awarded_contract_watch":
        p *= 0.1          # past-due (awarded-watch rows are intentionally dated)

    verdict = _classify(row)
    if verdict.decision == "REJECT" or verdict.matched_exclude:
        p *= 0.3          # relevance flagged a problem

    # Incumbent vulnerability (award_date may not exist yet — guard with get).
    award = _parse_date(row.get("award_date", "") or "")
    if award is not None and abs((today - award).days) <= 365:
        p *= 0.4          # recently awarded to someone else -> hard to displace
    else:
        p *= 0.8          # default modest incumbency discount

    return p


def strategic_fit(row: dict) -> float:
    """Beyond winnability: how much we WANT this — home region (esp. TX), core
    correctional/dorm segment, and recurring vehicles."""
    s = 1.0

    states = relevance.detect_states(_geo_text(row))
    if "TX" in states:
        s *= 1.15
    elif states & HOME_STATES:
        s *= 1.1

    verdict = _classify(row)
    lead_type = row.get("lead_type", "") or ""
    if lead_type in CORE_LEAD_TYPES or (set(verdict.context) & CORE_CONTEXT):
        s *= 1.2

    source = row.get("source", "") or ""
    if lead_type == "awarded_contract_watch" or RECURRING_RE.search(source):
        s *= 1.2

    return s


def compute(row: dict, today: date) -> tuple[int, dict]:
    """Return (win_score 0..100, factors dict rounded to 2dp). Handles both
    pipeline rows and lead rows."""
    pf = product_fit(row)
    vt = value_tier(row)
    wp = win_probability(row, today)
    sf = strategic_fit(row)
    score = round(min(100.0, pf * vt * wp * sf * 100.0))
    factors = {
        "pf": round(pf, 2),
        "vt": round(vt, 2),
        "wp": round(wp, 2),
        "sf": round(sf, 2),
    }
    return score, factors


def format_factors(factors: dict) -> str:
    """Compact, stable string for the win_factors CSV column."""
    return ";".join(f"{k}={factors[k]:.2f}" for k in ("pf", "vt", "wp", "sf"))


# ---------------------------------------------------------------------
# rank CLI
# ---------------------------------------------------------------------
def _load_rows(source: str) -> list[dict]:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if source == "leads":
        import lead_radar  # noqa: E402
        path = lead_radar.DEFAULT_REVIEW
        if not path.exists():
            return []
        return lead_radar.read_lead_rows(path)[1]
    import pipeline  # noqa: E402
    path = pipeline.DEFAULT_ACTIVE
    if not path.exists():
        return []
    return pipeline.read_rows(path)[1]


def _row_id(row: dict) -> str:
    return (row.get("opportunity_id") or row.get("lead_id")
            or row.get("title") or "(unknown)")


def cmd_rank(args: argparse.Namespace) -> int:
    today = args.today or date.today()
    rows = _load_rows(args.source)

    scored = []
    for row in rows:
        score, factors = compute(row, today)
        scored.append((score, row, factors))

    # win_score DESC, then due_date ASC (blanks last), then id for stability.
    def sort_key(item):
        score, row, _ = item
        due = row.get("due_date") or ""
        due_key = (1, "") if not due else (0, due)
        return (-score, due_key, _row_id(row))

    scored.sort(key=sort_key)
    if args.top is not None:
        scored = scored[: args.top]

    if not scored:
        print(f"(no rows for source={args.source})")
        return 0

    rows_out = [
        {
            "win": str(score),
            "id": _row_id(row),
            "title": (row.get("title") or "")[:50],
            "due": row.get("due_date") or "-",
            "factors": format_factors(factors),
        }
        for score, row, factors in scored
    ]
    cols = ("win", "id", "title", "due", "factors")
    widths = {c: max(len(c), max((len(r[c]) for r in rows_out), default=0)) for c in cols}
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print("  ".join("-" * widths[c] for c in cols))
    for r in rows_out:
        print("  ".join(r[c].ljust(widths[c]) for c in cols))
    return 0


def _parse_iso_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD ({exc})") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_rank = sub.add_parser("rank", help="Print opportunities ranked by win_score.")
    p_rank.set_defaults(func=cmd_rank)
    p_rank.add_argument("--source", choices=("pipeline", "leads"), default="pipeline")
    p_rank.add_argument("--top", type=int, default=None, help="Show only the top N rows.")
    p_rank.add_argument("--today", type=_parse_iso_date, default=None,
                        help="Date for due/award checks (default: today).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
