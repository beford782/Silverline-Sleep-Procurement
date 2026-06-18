#!/usr/bin/env python3
"""
relevance.py — central mattress-opportunity relevance filter.

Every ingest channel (SAM API, portal emails, future RSS/feeds) funnels its
raw text through `classify()`, which decides whether an item is a real
mattress/bedding opportunity. This replaces per-portal commodity-code
matching as the gate: noisy channels (broad "office/school furniture"
digests, web-search hits) get filtered here instead of flooding the
pipeline.

Decision bands:
  ACCEPT — a clear mattress/bedding signal (e.g. "mattress", "box spring").
  REVIEW — ambiguous: furniture/bedding-adjacent wording with no explicit
           mattress term (a human must confirm scope on the portal). This
           is the correct home for broad furniture co-op digests.
  REJECT — a hard-exclude family (concrete/scour mattress, aircraft, air
           mattress, recycling/disposal, reupholster/refinish), or no
           include signal at all (e.g. a registration-confirmation email).

Matching is whole-word / phrase based (regex word boundaries), NOT substring
counting — so "cot" no longer matches "Scott" and "foundation" no longer
fires on unrelated prose (a real bug in the old pipeline scorer).

Geography: an ACCEPT whose text clearly names a location OUTSIDE the home
service area is demoted to REVIEW (not rejected — location is often absent),
so the operator decides. Home states default to TX/OK/LA/MS/AR/NM.

Stdlib only. Pure functions; no I/O except the optional __main__ CLI.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field


HOME_STATES_DEFAULT = frozenset({"TX", "OK", "LA", "MS", "AR", "NM"})

# --- Vocabulary (tiers) ----------------------------------------------------
# Phrases are matched as whole words/phrases; internal spaces tolerate runs of
# whitespace and an optional hyphen where noted via the _phrase() compiler.

STRONG_INCLUDE = [
    "mattress", "mattresses",
    "box spring", "box springs", "boxspring", "boxsprings",
    "mattress foundation", "bed foundation",
    "bunk mattress", "cot mattress", "crib mattress",
    "dormitory mattress",
    "jail mattress", "correctional mattress", "detention mattress",
    "inmate mattress",
    # Commodity codes that unambiguously mean mattresses/bedding.
    "337910", "naics 337910",  # Mattress Manufacturing
    "psc 7210",                # Household Furnishings (mattresses, bedding sets)
]

WEAK_INCLUDE = [
    "bedding", "bed frame", "bed frames", "bunk bed", "bunk beds",
    "bunk", "bunks", "cot", "cots", "linens", "pillow", "pillows",
    "furniture", "furnishings", "ff&e", "ffe",
    "dormitory furniture", "residence hall furniture",
    "twin xl",  # student-housing mattress size; matches "twin-xl" too (phrase compiler)
    "psc 7105",  # Household Furniture (beds/frames; routes finished mattresses to 7210)
]

CONTEXT = [
    "correctional", "detention", "jail", "jails", "prison", "prisons",
    "inmate", "dorm", "dormitory", "residence hall", "student housing",
    "barracks", "shelter", "emergency shelter", "disaster",
    "hospital", "medical", "med-surg", "nursing home", "long-term care",
    "behavioral health", "university", "college", "school district",
    "housing authority",
]

# Hard kill — unambiguous false-positive families seen in real ingests.
HARD_EXCLUDE = [
    "concrete mattress", "articulated concrete", "concrete block mattress",
    "scour", "erosion control", "gabion",
    "aircraft", "aviation",
    "air mattress", "inflatable mattress", "air bed",
    "mattress recycling", "mattress disposal", "recycling services",
    "reupholster", "reupholstery", "refinish",
]

# Penalize / force REVIEW (broad catalogs, capability gaps, geography hints).
SOFT_EXCLUDE = [
    "office furniture", "school furniture", "classroom furniture",
    "desks", "filing cabinet", "lockers", "office supplies",
    "anti-ligature", "ligature resistant", "ligature-resistant",
    "overseas", "foreign",
]

# Procurement cues — signals that an item is an actual solicitation/buy, not
# news, a competitor catalog, or a forum post. Used by web/RSS channels via
# require_procurement so "jail mattress" news/retail chatter doesn't ACCEPT.
PROCUREMENT_CUES = [
    "rfp", "rfq", "rfi", "ifb", "invitation for bid", "invitation for bids",
    "invitation to bid", "request for proposal", "request for proposals",
    "request for quotation", "request for quote", "request for information",
    "solicitation", "sources sought", "procurement", "bid number", "bid no",
    "competitive sealed", "purchase order", "notice of award", "bid opportunity",
    "bid", "bids", "proposal", "quote",
]

# USPS code <-> handled via name list + ", ST" pattern (see detect_states).
_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT",
    "delaware": "DE", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME",
    "maryland": "MD", "massachusetts": "MA", "michigan": "MI",
    "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM",
    "new york": "NY", "north carolina": "NC", "north dakota": "ND",
    "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}
_USPS = set(_STATE_NAMES.values())


def _phrase(p: str) -> str:
    """Build a whole-word/phrase regex fragment with flexible whitespace."""
    # Escape, then let internal spaces match runs of whitespace; treat a
    # space or hyphen interchangeably so "fire retardant"/"fire-retardant"
    # and "med surg"/"med-surg" both match.
    parts = re.split(r"[ \-]+", p)
    body = r"[\s\-]+".join(re.escape(part) for part in parts)
    left = r"(?<![A-Za-z0-9])"
    right = r"(?![A-Za-z0-9])"
    return left + body + right


def _compile(words: list[str]) -> list[tuple[str, re.Pattern]]:
    return [(w, re.compile(_phrase(w), re.IGNORECASE)) for w in words]


_STRONG = _compile(STRONG_INCLUDE)
_WEAK = _compile(WEAK_INCLUDE)
_CONTEXT = _compile(CONTEXT)
_HARD = _compile(HARD_EXCLUDE)
_SOFT = _compile(SOFT_EXCLUDE)
_PROC = _compile(PROCUREMENT_CUES)
_STATE_NAME_RE = re.compile(
    r"(?<![A-Za-z])(" + "|".join(re.escape(n) for n in _STATE_NAMES) + r")(?![A-Za-z])",
    re.IGNORECASE,
)
_STATE_CODE_RE = re.compile(r",\s*(" + "|".join(sorted(_USPS)) + r")\b")


@dataclass
class Verdict:
    decision: str  # ACCEPT | REVIEW | REJECT
    confidence: int  # 0..100
    matched_include: list[str] = field(default_factory=list)
    matched_exclude: list[str] = field(default_factory=list)
    context: list[str] = field(default_factory=list)
    states: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _hits(text: str, compiled: list[tuple[str, re.Pattern]]) -> list[str]:
    return [w for w, rx in compiled if rx.search(text)]


def detect_states(text: str) -> set[str]:
    """USPS codes for any state named (full name anywhere, or ', ST' form)."""
    found = {_STATE_NAMES[m.group(1).lower()] for m in _STATE_NAME_RE.finditer(text)}
    found |= {m.group(1) for m in _STATE_CODE_RE.finditer(text)}
    return found


def _clamp(n: int, lo: int = 0, hi: int = 100) -> int:
    return max(lo, min(hi, n))


def has_procurement_cue(text: str) -> bool:
    """True if the text carries a solicitation/buy signal (RFP, bid, etc.)."""
    return bool(_hits(text or "", _PROC))


def classify(text: str, buyer: str = "", source: str = "",
             home_states: frozenset[str] = HOME_STATES_DEFAULT,
             require_procurement: bool = False) -> Verdict:
    """Classify free text as ACCEPT / REVIEW / REJECT for mattress relevance.

    require_procurement: for web/RSS sources, an item with a mattress signal
    but NO procurement cue (RFP/bid/solicitation/...) is demoted ACCEPT ->
    REVIEW, so news stories and competitor catalogs don't auto-accept.
    """
    blob = " ".join(p for p in (text or "", buyer or "", source or "") if p)

    hard = _hits(blob, _HARD)
    if hard:
        return Verdict("REJECT", 5, matched_exclude=hard,
                       reasons=[f"hard-exclude: {', '.join(hard)}"])

    strong = _hits(blob, _STRONG)
    weak = _hits(blob, _WEAK)
    context = _hits(blob, _CONTEXT)
    soft = _hits(blob, _SOFT)

    if not strong and not weak:
        return Verdict("REJECT", 0, reasons=["no mattress/bedding signal"])

    reasons: list[str] = []
    if strong:
        decision = "ACCEPT"
        conf = _clamp(80 + 5 * (len(strong) - 1) + (5 if context else 0))
        reasons.append(f"strong: {', '.join(strong)}")
        if soft:
            conf = _clamp(conf - 15)
            reasons.append(f"broad-catalog wording: {', '.join(soft)}")
    else:
        decision = "REVIEW"
        conf = _clamp(45 + (10 if context else 0) - (10 if soft else 0), 25, 60)
        reasons.append(f"weak only: {', '.join(weak)} (no explicit mattress term)")
        if context:
            reasons.append(f"institutional context: {', '.join(context)}")

    states = detect_states(blob)
    in_region = states & home_states
    out_region = states - home_states
    if states and not in_region and out_region:
        if decision == "ACCEPT":
            decision = "REVIEW"
            conf = _clamp(min(conf, 55), 25, 60)
        reasons.append(f"out-of-region: {', '.join(sorted(out_region))}")

    if require_procurement and decision == "ACCEPT" and not has_procurement_cue(blob):
        decision = "REVIEW"
        conf = _clamp(min(conf, 50), 25, 60)
        reasons.append("no procurement cue (web source — could be news/catalog)")

    return Verdict(decision, conf, matched_include=strong + weak,
                   matched_exclude=soft, context=context,
                   states=sorted(states), reasons=reasons)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print("usage: relevance.py \"text to classify\"", file=sys.stderr)
        return 2
    v = classify(" ".join(args))
    print(f"decision   : {v.decision}  (confidence {v.confidence})")
    print(f"include    : {v.matched_include}")
    print(f"exclude    : {v.matched_exclude}")
    print(f"context    : {v.context}")
    print(f"states     : {v.states}")
    for r in v.reasons:
        print(f"  - {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
