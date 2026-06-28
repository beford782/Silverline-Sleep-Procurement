#!/usr/bin/env python3
"""
demand_signal.py — pre-RFP institutional-mattress DEMAND classifier.

Where relevance.py gates actual procurement text (RFP / bid / solicitation for
mattresses), this module looks UPSTREAM of any solicitation: private-sector
construction and real-estate signals that a new pile of institutional beds is
about to exist. Hotels breaking ground, senior-living communities opening,
student-housing residence halls under construction, hospital bed towers,
county jails, homeless shelters — each is a future mattress buy that no
procurement portal has posted yet.

These signals carry construction / hospitality / real-estate language and
ZERO procurement cues — the mirror image of `relevance.classify()`. Catching
them early lets the operator reach the buyer (developer, GC, FF&E firm, owner)
BEFORE the RFP exists.

Decision bands:
  ACCEPT — a mattress-demand facility (hotel/senior/student/healthcare/
           correctional/shelter) PLUS a construction/renovation/opening
           trigger. This is a live pre-RFP demand signal.
  REVIEW — a facility is named but there's no project trigger (could be a
           travel review, a directory listing), OR an otherwise-ACCEPT signal
           that is out of region or collides with a non-demand exclude.
  REJECT — a non-demand construction type (office/retail/warehouse/...) with no
           facility, mattress retail/recycling noise, or simply no facility at
           all.

It REUSES relevance.py's pure helpers (`_compile`/`_phrase`, `detect_states`,
`HOME_STATES_DEFAULT`) for matching and geography, but never calls
relevance.classify(); the two classifiers are independent.

Stdlib only. Pure functions; no I/O except the optional __main__ CLI.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse relevance.py's whole-word phrase compiler, state detection, and home
# states so the two classifiers never drift on matching or geography rules.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relevance  # noqa: E402


SEGMENTS = ("hotel", "senior-living", "student-housing", "healthcare",
            "correctional", "shelter")
STAGES = ("planned", "proposed", "under-construction", "renovation",
          "opening", "delivered")

# --- Lexicon ---------------------------------------------------------------
# Project verbs map a construction/real-estate trigger phrase to a project
# stage. Matching reuses relevance._compile (whole-word/phrase, hyphen ==
# space), so "pip" never fires inside "pipeline" and "inn" never inside "winner".
_PROJECT_STAGE_BY_VERB: dict[str, str] = {
    # under-construction — ground is broken / steel is rising
    "breaks ground": "under-construction",
    "groundbreaking": "under-construction",
    "broke ground": "under-construction",
    "under construction": "under-construction",
    "begins construction": "under-construction",
    "tops out": "under-construction",
    "topping out": "under-construction",
    # opening — finishing / about to deliver
    "to open": "opening",
    "opening": "opening",
    "slated to open": "opening",
    "set to open": "opening",
    "scheduled to open": "opening",
    "will open": "opening",
    "expected to open": "opening",
    "delivering": "opening",
    "delivers": "opening",
    "nearing completion": "opening",
    # renovation — re-flag / PIP / refresh (mattresses get swapped)
    "renovation": "renovation",
    "renovating": "renovation",
    "property improvement plan": "renovation",
    "pip": "renovation",
    "re-flag": "renovation",
    "reflag": "renovation",
    "rebrand": "renovation",
    "repositioning": "renovation",
    "soft goods": "renovation",
    "guestroom refresh": "renovation",
    # planned / proposed — entitlement / pre-construction
    "planned": "planned",
    "proposed": "proposed",
    "approved": "planned",
    "rezoned": "planned",
    "permit issued": "planned",
    "plans to build": "planned",
    "to be built": "planned",
    "development of": "planned",
    # delivered — already open
    "completed construction": "delivered",
    "delivered": "delivered",
    "now open": "delivered",
    "grand opening": "delivered",
    "opens its doors": "delivered",
}
PROJECT_VERBS = list(_PROJECT_STAGE_BY_VERB)

# Stage priority when several verbs co-occur (e.g. "breaks ground ... opening
# Q3 2027"): the earliest, most-actionable physical stage wins. Picking
# under-construction over a downstream "opening" mention keeps the signal tied
# to the live project rather than its eventual ribbon-cutting.
_STAGE_PRIORITY = ("under-construction", "renovation", "delivered",
                   "opening", "proposed", "planned")

FACILITY_NOUNS_BY_SEGMENT: dict[str, list[str]] = {
    "hotel": [
        "hotel", "resort", "inn", "motel", "suites", "hospitality",
        "extended stay",
        # brand flags
        "marriott", "hilton", "hyatt", "ihg", "holiday inn", "hampton",
        "fairfield", "courtyard", "wyndham", "la quinta", "best western",
        "residence inn", "staybridge",
    ],
    "senior-living": [
        "senior living", "assisted living", "memory care", "independent living",
        "skilled nursing", "nursing facility", "nursing home", "snf", "ccrc",
        "continuing care", "life plan community", "long-term care",
    ],
    "student-housing": [
        "student housing", "residence hall", "dormitory", "dorm",
        "purpose-built student", "pbsa", "off-campus housing",
        "university housing",
    ],
    "healthcare": [
        "hospital", "medical center", "patient tower", "bed tower", "inpatient",
        "behavioral health hospital", "psychiatric hospital", "acute care",
        "ltach",
    ],
    "correctional": [
        "jail", "county jail", "detention center", "detention facility",
        "correctional facility", "correctional center", "prison",
        "juvenile detention", "re-entry facility", "regional jail",
    ],
    "shelter": [
        "homeless shelter", "emergency shelter", "navigation center",
        "transitional housing", "migrant shelter", "workforce housing",
        "crew housing", "man camp",
    ],
}

# Non-demand hard kill — construction types that are never institutional beds,
# plus mattress retail/recycling noise (the spirit of relevance's wrong-product
# excludes). These REJECT only when NO facility noun is present; when a facility
# co-occurs they demote ACCEPT -> REVIEW for a human glance.
NON_DEMAND_EXCLUDE = [
    "office building", "office tower", "retail", "shopping center", "warehouse",
    "distribution center", "data center", "parking garage", "highway", "bridge",
    "water treatment", "solar farm", "industrial park", "manufacturing plant",
    "single-family", "subdivision",
    # mattress retail / wrong-product noise
    "mattress recycling", "mattress disposal", "mattress store", "mattress sale",
    "mattress firm", "air mattress", "concrete mattress",
]

# Scale: keys/rooms/beds/units/suites. Take the MAX numeric match.
SCALE_RE = re.compile(r"(\d[\d,]*)\s*[- ]?\s*(keys?|rooms?|beds?|units?|suites?)",
                      re.IGNORECASE)

# Dates: an opening/completion year near a project verb, a bare quarter+year, a
# season+year, or a bare year. Quarter (when present) drives the buy-window month.
_DATE_VERB_RE = re.compile(
    r"(?:open|opening|complete|completion|delivery|deliver)\w*\s+"
    r"(?:in\s+)?(?:(Q[1-4])\s+)?(20\d{2})",
    re.IGNORECASE,
)
_QUARTER_YEAR_RE = re.compile(r"(Q[1-4])\s+(20\d{2})", re.IGNORECASE)
_SEASON_YEAR_RE = re.compile(r"(spring|summer|fall|winter)\s+(20\d{2})",
                             re.IGNORECASE)
_BARE_YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?!\d)")

_QUARTER_MONTH = {"Q1": "03", "Q2": "06", "Q3": "09", "Q4": "12"}

# Compile lexicons via relevance's shared helper.
_PROJECT = relevance._compile(PROJECT_VERBS)
_FACILITY = [(seg, relevance._compile(FACILITY_NOUNS_BY_SEGMENT[seg]))
             for seg in SEGMENTS]
_EXCLUDE = relevance._compile(NON_DEMAND_EXCLUDE)


@dataclass
class DemandVerdict:
    decision: str            # ACCEPT | REVIEW | REJECT
    confidence: int          # 0..100
    segment: str = ""
    scale_value: int | None = None
    scale_unit: str = ""     # keys|rooms|beds|units
    project_stage: str = ""  # one of STAGES
    est_completion_date: str = ""   # "YYYY" or ""
    est_buy_window: str = ""        # "YYYY-MM" derived, or ""
    states: list[str] = field(default_factory=list)
    matched_project: list[str] = field(default_factory=list)
    matched_facility: list[str] = field(default_factory=list)
    matched_exclude: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _hits(text: str, compiled: list[tuple[str, re.Pattern]]) -> list[str]:
    return [w for w, rx in compiled if rx.search(text)]


def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))


def _detect_segment(text: str) -> tuple[str, list[str]]:
    """First-match-priority over the segment dict (deterministic, like
    lead_radar's lead-type families): the first SEGMENT with a facility-noun
    hit wins, returning (segment, hits). No hit -> ("", [])."""
    for seg, compiled in _FACILITY:
        hits = _hits(text, compiled)
        if hits:
            return seg, hits
    return "", []


def _detect_stage(verbs: list[str]) -> str:
    """Pick the highest-priority stage among matched project verbs."""
    stages = {_PROJECT_STAGE_BY_VERB[v] for v in verbs}
    for stage in _STAGE_PRIORITY:
        if stage in stages:
            return stage
    return ""


def _parse_scale(text: str) -> tuple[int | None, str]:
    """Max (value, unit) across scale matches; commas stripped."""
    best: tuple[int, str] | None = None
    for num, unit in SCALE_RE.findall(text):
        val = int(num.replace(",", ""))
        if best is None or val > best[0]:
            best = (val, unit.lower())
    return (None, "") if best is None else best


def _parse_date(text: str) -> tuple[str, str]:
    """Return (year, quarter) best-effort. quarter is '' or 'Q1'..'Q4'."""
    m = _DATE_VERB_RE.search(text)
    if m:
        year = m.group(2)
        quarter = (m.group(1) or "").upper()
        if not quarter:
            mq = _QUARTER_YEAR_RE.search(text)
            if mq:
                quarter = mq.group(1).upper()
        return year, quarter
    m = _QUARTER_YEAR_RE.search(text)
    if m:
        return m.group(2), m.group(1).upper()
    m = _SEASON_YEAR_RE.search(text)
    if m:
        return m.group(2), ""
    m = _BARE_YEAR_RE.search(text)
    if m:
        return m.group(1), ""
    return "", ""


def _buy_window(year: str, quarter: str) -> str:
    """Derive the YYYY-MM buy window. Quarter -> its closing month; otherwise
    month 01 (act now). No year -> ''."""
    if not year:
        return ""
    month = _QUARTER_MONTH.get(quarter, "01")
    return f"{year}-{month}"


def classify_demand(text: str, source: str = "",
                    home_states=relevance.HOME_STATES_DEFAULT) -> DemandVerdict:
    """Classify free text as ACCEPT / REVIEW / REJECT for pre-RFP institutional
    mattress demand. See module docstring for the bands."""
    blob = " ".join(p for p in (text or "", source or "") if p)

    segment, facility = _detect_segment(blob)
    verbs = _hits(blob, _PROJECT)
    stage = _detect_stage(verbs)
    exclude = _hits(blob, _EXCLUDE)
    scale_value, scale_unit = _parse_scale(blob)
    year, quarter = _parse_date(blob)
    est_completion_date = year
    est_buy_window = _buy_window(year, quarter)
    states = relevance.detect_states(blob)

    def verdict(decision: str, conf: int, reasons: list[str]) -> DemandVerdict:
        return DemandVerdict(
            decision=decision,
            confidence=_clamp(conf),
            segment=segment,
            scale_value=scale_value,
            scale_unit=scale_unit,
            project_stage=stage if decision != "REJECT" else "",
            est_completion_date=est_completion_date,
            est_buy_window=est_buy_window,
            states=sorted(states),
            matched_project=verbs,
            matched_facility=facility,
            matched_exclude=exclude,
            reasons=reasons,
        )

    # Band 1 & 2: no facility noun -> not a mattress-demand signal.
    if not segment:
        if exclude:
            return verdict("REJECT", 5,
                           [f"non-demand exclude, no facility: {', '.join(exclude)}"])
        return verdict("REJECT", 0, ["no mattress-demand facility"])

    reasons = [f"facility ({segment}): {', '.join(facility)}"]

    if verbs:
        # Band 3: facility + project trigger -> live demand signal.
        decision = "ACCEPT"
        conf = 70
        reasons.append(f"project trigger: {', '.join(verbs)} -> {stage}")
        if scale_value is not None:
            conf += 10
            reasons.append(f"scale: {scale_value} {scale_unit}")
        if est_completion_date:
            conf += 10
            reasons.append(f"completion: {est_completion_date}"
                           + (f" ({quarter})" if quarter else ""))
        if exclude:
            decision = "REVIEW"
            conf = _clamp(min(conf, 55), 25, 60)
            reasons.append(f"non-demand exclude co-occurs -> review: "
                           f"{', '.join(exclude)}")
    else:
        # Band 4: facility named but no construction/renovation trigger.
        decision = "REVIEW"
        conf = _clamp(40 + (10 if scale_value is not None else 0), 30, 55)
        reasons.append("facility named but no project trigger (construction/"
                       "renovation/opening)")

    # Band 5: geography — an ACCEPT clearly outside the home area is demoted to
    # REVIEW (mirrors relevance's out-of-region rule). Location is often absent,
    # so silence never demotes.
    in_region = states & home_states
    out_region = states - home_states
    if states and not in_region and out_region and decision == "ACCEPT":
        decision = "REVIEW"
        conf = _clamp(min(conf, 55), 25, 60)
        reasons.append(f"out-of-region: {', '.join(sorted(out_region))}")

    return verdict(decision, conf, reasons)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    text = " ".join(args) if args else sys.stdin.read()
    if not text.strip():
        print("usage: demand_signal.py \"construction/opening headline\"",
              file=sys.stderr)
        return 2
    v = classify_demand(text)
    print(f"decision   : {v.decision}  (confidence {v.confidence})")
    print(f"segment    : {v.segment}")
    print(f"scale      : {v.scale_value} {v.scale_unit}".rstrip())
    print(f"stage      : {v.project_stage}")
    print(f"completion : {v.est_completion_date}")
    print(f"buy window : {v.est_buy_window}")
    print(f"states     : {v.states}")
    print(f"project    : {v.matched_project}")
    print(f"facility   : {v.matched_facility}")
    print(f"exclude    : {v.matched_exclude}")
    for r in v.reasons:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
