#!/usr/bin/env python3
"""
ingest_permits.py — municipal building permits -> Demand Radar rows.

Issued building permits are a pre-RFP demand signal: a hotel finish-out, a
student-housing tower, a senior-living remodel or a shelter build-out each
means a pile of institutional beds is about to be bought, months before any
solicitation exists. This adapter pulls issued construction permits from a
city's open-data API and writes Demand Radar rows the same way the RSS demand
path (tools/ingest_rss.py, kind == "demand") does: classified by
tools/demand_signal.py, deduped against the review file + archive, written
atomically through tools/demand_radar.py. It never touches the bid pipeline.

Austin (Socrata, dataset 3syk-w9eu "Issued Construction Permits") is the pilot.
The config (configs/permits.json) is a list of sources so more cities can be
added later; only the "socrata" adapter is implemented today.

Facts the design is built around (verified on live Austin data):
  - Each project spawns one permit per trade (BP building, EP electrical,
    MP mechanical, PP plumbing) with the same description. Only BP is the
    project signal; the live query filters permittype server-side.
  - One project can issue several BP permits (one per floor / building). Records
    are grouped into ONE signal per (masterpermitnum or project_id) + site
    address stem; the permit numbers, floors and buildings land in notes.
  - Keyword hits contain trade noise ("Generator replacement ... shelter
    building", "concrete repairs in the Hotels Parking Garage"). A small
    config `exclude_terms` list sends those to the reject log; no heavy NLP.
  - Contractor person names / phones / addresses are NEVER requested or
    stored. contractor_company_name (a business) may be noted as "GC: <name>".

Usage:
    python tools/ingest_permits.py --config configs/permits.json --dry-run
    python tools/ingest_permits.py --config configs/permits.json \
        --fixture tests/fixtures/austin_permits_sample.json --dry-run
    python tools/ingest_permits.py --config configs/permits.json \
        --reject-log logs/rejects/_permits.csv

Exit code 0 on success (including "no new rows"); non-zero when ANY configured
source fails to fetch or parse, so a network failure never looks like a quiet
day. Stdlib only (urllib + json + csv).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = REPO_ROOT / "configs" / "permits.json"
DEFAULT_TIMEOUT_S = 30
USER_AGENT = "silverline-sleep-procurement/1.0"
DEFAULT_LOOKBACK_DAYS = 14
DEFAULT_LIMIT = 500

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_radar  # noqa: E402
import demand_signal  # noqa: E402
import pii_lint  # noqa: E402
import relevance  # noqa: E402


# The fixed Socrata $select. Deliberately EXCLUDES contractor_phone,
# contractor_full_name, contractor_address1/2 (PII) — do not add them.
SELECT_FIELDS = [
    "permit_number", "permittype", "permit_type_desc", "permit_class_mapped",
    "work_class", "description", "permit_location", "original_address1",
    "original_city", "original_state", "original_zip", "applieddate",
    "issue_date", "status_current", "total_job_valuation", "housing_units",
    "number_of_floors", "total_new_add_sqft", "remodel_repair_sqft",
    "project_id", "masterpermitnum", "contractor_company_name", "link",
]
FORBIDDEN_FIELDS = ("contractor_phone", "contractor_full_name",
                    "contractor_address1", "contractor_address2")

REJECT_HEADER = ["rejected_date", "source", "permit_number", "issue_date",
                 "work_class", "reason", "description", "source_url"]

SEGMENT_LABELS = {
    "hotel": "Hotel",
    "senior-living": "Senior living",
    "student-housing": "Student housing",
    "healthcare": "Healthcare",
    "correctional": "Correctional",
    "shelter": "Shelter",
}

# When the demand classifier finds no facility noun (its lexicon wants
# "homeless shelter" / "skilled nursing"; a permit just says "shelter" or
# "nursing"), fall back to the segment implied by the config keyword that
# matched. Order matters: first hit wins.
KEYWORD_SEGMENT_FALLBACK: list[tuple[str, str]] = [
    ("hotel", "hotel"), ("motel", "hotel"), ("inn ", "hotel"), ("suites", "hotel"),
    ("resort", "hotel"), ("hospitality", "hotel"),
    ("dormitory", "student-housing"), ("dorm", "student-housing"),
    ("residence hall", "student-housing"), ("student housing", "student-housing"),
    ("assisted living", "senior-living"), ("senior living", "senior-living"),
    ("memory care", "senior-living"), ("skilled nursing", "senior-living"),
    ("nursing", "senior-living"),
    ("behavioral health", "healthcare"),
    ("detention", "correctional"), ("jail", "correctional"),
    ("shelter", "shelter"), ("barracks", "shelter"),
]

# Trailing "Floor 11" / "Level 3" tokens are split off the description so the
# floors of one project share a facility_name (and therefore one demand_id).
_FLOOR_TAIL_RE = re.compile(r"[\s,\-–]*(?:\(|\b)(?:floor|level|fl\.?)\s*#?\s*(\d+)\)?\s*$", re.I)
_FLOOR_ANY_RE = re.compile(r"\bfloor\s*#?\s*(\d+)\b", re.I)
_ADDRESS_UNIT_RE = re.compile(
    r"\s+(?:BLDG|BUILDING|STE|SUITE|UNIT|APT|FL|FLOOR|RM|ROOM)\s+\S+$", re.I)
_MAIN_SUFFIX_RE = re.compile(r"[\s*]*\bMAIN\b[\s*]*$", re.I)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WS_RE = re.compile(r"\s+")

FACILITY_STEM_MAX = 88   # longest label "Senior living permit: " (22) + 88 = 110 chars


# ---------------------------------------------------------------------------
# Config + SoQL
# ---------------------------------------------------------------------------
def load_config(path: Path) -> list[dict]:
    with Path(path).open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    if not isinstance(cfg, list):
        raise ValueError(f"{path}: expected a JSON array of sources")
    for src in cfg:
        if not src.get("url") or not src.get("source"):
            raise ValueError(f"{path}: every source needs 'url' and 'source'")
    return cfg


def _soql_quote(value: str) -> str:
    """Single-quote a SoQL string literal, doubling embedded quotes."""
    return "'" + str(value).replace("'", "''") + "'"


def build_socrata_url(src: dict, since: str) -> str:
    """Pure: the Socrata GET URL for one source. `since` is YYYY-MM-DD.

    $where = issue_date > since AND permit_class_mapped = X AND permittype in
    (BP) AND (upper(description) LIKE '%HOTEL%' OR ...). The $select is the
    fixed field list above (never contractor person/phone/address fields).
    """
    clauses = [f"issue_date > {_soql_quote(since + 'T00:00:00')}"]
    pcm = src.get("permit_class_mapped")
    if pcm:
        clauses.append(f"permit_class_mapped = {_soql_quote(pcm)}")
    ptypes = src.get("permit_types") or []
    if ptypes:
        clauses.append("permittype in (" + ", ".join(_soql_quote(p) for p in ptypes) + ")")
    keywords = src.get("keywords") or []
    if keywords:
        likes = " OR ".join(
            f"upper(description) LIKE {_soql_quote('%' + kw.upper() + '%')}" for kw in keywords)
        clauses.append(f"({likes})")
    params = [
        ("$select", ", ".join(SELECT_FIELDS)),
        ("$where", " AND ".join(clauses)),
        ("$order", "issue_date DESC"),
        ("$limit", str(int(src.get("limit") or DEFAULT_LIMIT))),
    ]
    return src["url"] + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)


def fetch_json(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> list[dict]:
    """GET a JSON array. Raises OSError/ValueError on any fetch/parse problem."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    token = os.environ.get("SOCRATA_APP_TOKEN", "").strip()
    if token:
        headers["X-App-Token"] = token
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    if not isinstance(data, list):
        raise ValueError(f"expected a JSON array, got {type(data).__name__}")
    return data


# ---------------------------------------------------------------------------
# Record helpers (pure)
# ---------------------------------------------------------------------------
def _norm_date(value) -> str:
    v = (str(value or "")).strip()
    return v[:10] if len(v) >= 10 and v[4] == "-" and v[7] == "-" else ""


def _collapse(text) -> str:
    return _WS_RE.sub(" ", str(text or "")).strip()


def _record_url(rec: dict) -> str:
    link = rec.get("link")
    if isinstance(link, dict):
        return str(link.get("url") or "").strip()
    return str(link or "").strip()


def _site_address(rec: dict) -> str:
    return _collapse(rec.get("original_address1") or rec.get("permit_location") or "").upper()


def address_stem(address: str) -> str:
    """Site address without a trailing BLDG/STE/UNIT qualifier (repeatedly)."""
    stem = _collapse(address).upper()
    for _ in range(3):
        new = _ADDRESS_UNIT_RE.sub("", stem)
        if new == stem:
            break
        stem = new
    return stem


def _address_unit(address: str) -> str:
    """The qualifier address_stem() removed ("BLDG 100"), or ''."""
    full = _collapse(address).upper()
    stem = address_stem(full)
    return full[len(stem):].strip() if full.startswith(stem) and full != stem else ""


def clean_contractor(name) -> str:
    """Drop Austin's '*MAIN**' / '****MAIN***' suffix and tidy whitespace."""
    out = _MAIN_SUFFIX_RE.sub("", _collapse(name))
    return out.strip(" *").strip()


def description_stem(description: str) -> str:
    """Description with a trailing 'Floor N' token removed, whitespace collapsed."""
    text = _collapse(description)
    return _FLOOR_TAIL_RE.sub("", text).strip(" ,-–")


def first_sentence(text: str, max_len: int = FACILITY_STEM_MAX) -> str:
    text = _collapse(text)
    if not text:
        return ""
    sent = _SENTENCE_SPLIT_RE.split(text, maxsplit=1)[0].strip()
    if len(sent) > max_len:
        cut = sent[:max_len]
        if " " in cut:
            cut = cut[:cut.rfind(" ")]
        sent = cut.rstrip(" ,;:-/")
    return sent.rstrip(".").strip()


def floors_in(description: str) -> list[str]:
    return [m.group(1) for m in _FLOOR_ANY_RE.finditer(description or "")]


def _num(value) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def add_months(iso_date: str, months: int) -> str:
    """YYYY-MM that is `months` after the month of YYYY-MM-DD (year rollover safe)."""
    d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    idx = d.year * 12 + (d.month - 1) + months
    return f"{idx // 12:04d}-{idx % 12 + 1:02d}"


def stage_from_work_class(work_class: str) -> str:
    wc = (work_class or "").lower()
    if not wc:
        return ""
    if "new" in wc or "addition" in wc:
        return "under-construction"
    if any(k in wc for k in ("remodel", "upgrade", "projecting", "repair",
                             "change out", "change-out", "alteration", "renovation")):
        return "renovation"
    return ""


def derive_buy_window(issue_date: str, work_class: str) -> str:
    """New construction buys ~15 months after the building permit; a remodel /
    upgrade / finish-out buys ~3 months after."""
    if not issue_date:
        return ""
    months = 15 if stage_from_work_class(work_class) == "under-construction" else 3
    return add_months(issue_date, months)


def scrub_pii(text: str) -> str:
    """Backstop so a generated field can never trip tools/pii_lint.py.

    A Title Case street address in a description is public site data, so it is
    kept but UPPERCASED (the lint's address regex wants Title Case words);
    phone / EIN shaped tokens are dropped outright.
    """
    out = text or ""
    for kind, pattern in pii_lint.PATTERNS:
        if kind == "street-address":
            out = pattern.sub(lambda m: m.group(0).upper(), out)
        else:
            out = pattern.sub("[removed]", out)
    return out


def _matched_keyword(text: str, keywords: list[str]) -> str:
    low = (text or "").lower()
    for kw in keywords:
        if kw.lower() in low:
            return kw
    return ""


def _matched_exclude(text: str, compiled) -> str:
    for term, rx in compiled:
        if rx.search(text or ""):
            return term
    return ""


def _year_is_contextual(text: str) -> bool:
    """True when demand_signal's date came from an opening/quarter/season phrase
    rather than a bare 20xx (permit text is full of case numbers like
    SP-2026-0151C, which are not completion years)."""
    return bool(demand_signal._DATE_VERB_RE.search(text)
                or demand_signal._QUARTER_YEAR_RE.search(text)
                or demand_signal._SEASON_YEAR_RE.search(text))


# ---------------------------------------------------------------------------
# Filter -> group -> row
# ---------------------------------------------------------------------------
def _reject(rec: dict, source: str, reason: str, today: str) -> dict:
    return {
        "rejected_date": today,
        "source": source,
        "permit_number": _collapse(rec.get("permit_number")),
        "issue_date": _norm_date(rec.get("issue_date")),
        "work_class": _collapse(rec.get("work_class")),
        "reason": reason,
        "description": _collapse(rec.get("description"))[:160],
        "source_url": _record_url(rec),
    }


def filter_records(records: list[dict], src: dict, today: str
                   ) -> tuple[list[dict], list[dict]]:
    """Per-record gates: permit type, work class, keyword, exclude terms.
    Returns (kept, rejected_log_rows)."""
    ptypes = {p.upper() for p in (src.get("permit_types") or [])}
    excluded_wc = {w.lower() for w in (src.get("exclude_work_class") or [])}
    keywords = src.get("keywords") or []
    compiled_excludes = relevance._compile(src.get("exclude_terms") or [])
    source = src["source"]
    kept: list[dict] = []
    rejected: list[dict] = []
    for rec in records:
        ptype = _collapse(rec.get("permittype")).upper()
        if ptypes and ptype not in ptypes:
            rejected.append(_reject(rec, source, f"non_bp:{ptype or '?'}", today))
            continue
        wc = _collapse(rec.get("work_class"))
        if wc.lower() in excluded_wc:
            rejected.append(_reject(rec, source, f"work_class_excluded:{wc}", today))
            continue
        desc = _collapse(rec.get("description"))
        if keywords and not _matched_keyword(desc, keywords):
            rejected.append(_reject(rec, source, "no_keyword", today))
            continue
        term = _matched_exclude(desc, compiled_excludes)
        if term:
            rejected.append(_reject(rec, source, f"exclude_term:{term}", today))
            continue
        kept.append(rec)
    return kept, rejected


def group_records(records: list[dict]) -> list[list[dict]]:
    """One project = one group: (masterpermitnum or project_id) + address stem.
    Groups keep first-seen order; members are sorted by permit_number."""
    groups: dict[tuple, list[dict]] = {}
    for rec in records:
        anchor = _collapse(rec.get("masterpermitnum")) or _collapse(rec.get("project_id")) \
            or _collapse(rec.get("permit_number"))
        key = (anchor, address_stem(_site_address(rec)))
        groups.setdefault(key, []).append(rec)
    out = []
    for members in groups.values():
        out.append(sorted(members, key=lambda r: _collapse(r.get("permit_number"))))
    return out


def group_to_row(group: list[dict], src: dict, today: str) -> dict:
    """Map one grouped permit signal onto a Demand Radar row."""
    primary = group[0]
    source = src["source"]
    city = src.get("city") or _collapse(primary.get("original_city")).title()
    state = (src.get("state") or _collapse(primary.get("original_state")) or "").upper()
    work_class = _collapse(primary.get("work_class"))
    type_desc = _collapse(primary.get("permit_type_desc"))
    keywords = src.get("keywords") or []

    # Unique description stems, primary first.
    stems: list[str] = []
    for rec in group:
        stem = description_stem(rec.get("description"))
        if stem and stem not in stems:
            stems.append(stem)
    text = " | ".join(stems + [p for p in (work_class, type_desc) if p])

    verdict = demand_signal.classify_demand(text, source=source)
    reasons = list(verdict.reasons)
    if verdict.decision == "REJECT":
        verdict.decision = "REVIEW"
        reasons.append("classifier=REJECT, kept as permit signal")
    if not verdict.segment:
        kw = _matched_keyword(text, [k for k, _ in KEYWORD_SEGMENT_FALLBACK]) or \
            _matched_keyword(text, keywords)
        seg = next((s for k, s in KEYWORD_SEGMENT_FALLBACK if k == kw), "")
        if seg:
            verdict.segment = seg
            reasons.append(f"segment from permit keyword: {kw.strip()}")
    if not verdict.project_stage:
        derived = stage_from_work_class(work_class)
        if derived:
            verdict.project_stage = derived
            reasons.append(f"stage derived from work_class {work_class}")

    issue_dates = sorted(d for d in (_norm_date(r.get("issue_date")) for r in group) if d)
    applied_dates = sorted(d for d in (_norm_date(r.get("applieddate")) for r in group) if d)
    issued = issue_dates[-1] if issue_dates else ""
    if verdict.est_completion_date and not _year_is_contextual(text):
        # A bare 20xx in permit text is a case number, not a completion year.
        verdict.est_completion_date = ""
        verdict.est_buy_window = ""
    if not verdict.est_buy_window and issued:
        verdict.est_buy_window = derive_buy_window(issued, work_class)
        reasons.append("buy-window derived from permit issue date")
    verdict.states = [state] if state else []

    label = SEGMENT_LABELS.get(verdict.segment, "Facility")
    facility_name = scrub_pii(f"{label} permit: {first_sentence(stems[0] if stems else text)}")

    row = demand_radar.build_demand_row(facility_name, source, verdict, today,
                                        source_url=_record_url(primary))

    site = address_stem(_site_address(primary))
    zip_code = _collapse(primary.get("original_zip"))
    location = ", ".join(p for p in (site, city) if p)
    tail = " ".join(p for p in (state, zip_code) if p)
    if tail:
        location = f"{location}, {tail}" if location else tail
    row["location"] = location
    # Identity includes the site so two projects with the same generic
    # description ("Hotel guestroom renovation") at different addresses stay
    # distinct; demand_match_keys derives the same id, so dedupe stays shared
    # with the RSS demand path (see match_keys for the URL-key exception).
    row["demand_id"] = demand_radar.demand_id_for(source, verdict.segment, facility_name, location)

    valuation = sum(v for v in (_num(r.get("total_job_valuation")) for r in group) if v > 0)
    row["est_value"] = str(int(valuation)) if valuation > 0 else ""
    row["owner_operator"] = ""

    # Notes: reasons + permit facts (business names only; no people, no phones).
    permit_list = ", ".join(_collapse(r.get("permit_number")) for r in group)
    master = _collapse(primary.get("masterpermitnum"))
    master_txt = f", master {master}" if master else ""
    notes = list(reasons)
    notes.append(f"permits: {permit_list} ({len(group)} {primary.get('permittype', 'BP')}{master_txt})")
    if work_class:
        notes.append(f"work_class: {work_class}")
    dates_bits = []
    if applied_dates:
        dates_bits.append(f"applied {applied_dates[0]}")
    if issued:
        dates_bits.append(f"issued {issued}")
    if dates_bits:
        notes.append(", ".join(dates_bits))
    floors: list[str] = []
    for rec in group:
        for f in floors_in(rec.get("description") or ""):
            if f not in floors:
                floors.append(f)
    if floors:
        notes.append("floors: " + ", ".join(sorted(floors, key=int)))
    units: list[str] = []
    for rec in group:
        u = _address_unit(_site_address(rec))
        if u and u not in units:
            units.append(u)
    if units:
        notes.append("site units: " + ", ".join(units))
    gc = clean_contractor(primary.get("contractor_company_name"))
    if gc:
        notes.append(f"GC: {gc}")
    housing_units = max((_num(r.get("housing_units")) for r in group), default=0)
    if housing_units > 1:
        notes.append(f"housing_units: {int(housing_units)}")
    sqft_new = max((_num(r.get("total_new_add_sqft")) for r in group), default=0)
    sqft_remodel = max((_num(r.get("remodel_repair_sqft")) for r in group), default=0)
    if sqft_new > 0:
        notes.append(f"new sqft: {int(sqft_new)}")
    if sqft_remodel > 0:
        notes.append(f"remodel sqft: {int(sqft_remodel)}")
    row["notes"] = scrub_pii("; ".join(n for n in notes if n))
    return row


def match_keys(row: dict) -> set[str]:
    """demand_radar.demand_match_keys with a permit-safe URL key.

    demand_radar.normalize_source_url drops the query string, but a permit
    portal link carries its identity THERE (Austin: ...?t_selected_folderrsn=N),
    so every permit would collapse onto one URL key. Keep the id/facility+
    location keys unchanged and key the URL with its query intact.
    """
    keys = {k for k in demand_radar.demand_match_keys(row) if not k.startswith("url:")}
    url = (row.get("source_url") or "").strip()
    if url:
        u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url, flags=re.I)
        u = re.sub(r"^www\.", "", u.split("#", 1)[0], flags=re.I)
        keys.add(f"url:{u.rstrip('/').lower()}")
    return keys


def ingest_source(records: list[dict], src: dict, today: str,
                  known_keys: set[str]) -> dict:
    """Run one source's records through filter -> group -> row -> dedupe.

    `known_keys` (match_keys of review + archive + rows produced earlier
    in this run) is updated in place with every accepted row's keys.
    Returns {"fetched", "grouped", "accepted": rows, "rejected": log rows,
    "duplicates": n}.
    """
    kept, rejected = filter_records(records, src, today)
    groups = group_records(kept)
    accepted: list[dict] = []
    duplicates = 0
    for group in groups:
        row = group_to_row(group, src, today)
        keys = match_keys(row)
        if keys & known_keys:
            duplicates += 1
            rejected.append(_reject(group[0], src["source"], "duplicate", today))
            continue
        known_keys |= keys
        accepted.append(row)
    return {"fetched": len(records), "grouped": len(groups),
            "accepted": accepted, "rejected": rejected, "duplicates": duplicates}


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def _read_existing_demand_or_empty(path: Path) -> list[dict]:
    if not path.exists():
        return []
    _, rows = demand_radar.read_demand_rows(path)
    return rows


def append_reject_log(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=REJECT_HEADER, lineterminator="\n",
                                extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _error_message(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    reason = getattr(exc, "reason", None)
    return str(reason) if reason is not None else f"{type(exc).__name__}: {exc}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="JSON list of permit sources (default: %(default)s)")
    parser.add_argument("--since-days", type=int, default=None,
                        help="Override every source's lookback_days (default: per source, 14).")
    parser.add_argument("--demand", default=str(demand_radar.DEFAULT_REVIEW),
                        help="Demand Radar CSV write target (default: %(default)s)")
    parser.add_argument("--demand-archive", default=str(demand_radar.DEFAULT_ARCHIVE),
                        help="Demand Radar archive consulted for dedup only; never written.")
    parser.add_argument("--reject-log", default=None,
                        help="CSV to append rejected/duplicate permits to (own schema).")
    parser.add_argument("--fixture", default=None,
                        help="Read a JSON array of permit records from a file instead of the "
                             "network (first configured source's settings apply).")
    parser.add_argument("--today", default=None, help="Override today's date (YYYY-MM-DD).")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; write nothing.")
    args = parser.parse_args(argv)

    if args.today:
        try:
            today_d = datetime.strptime(args.today, "%Y-%m-%d").date()
        except ValueError:
            print(f"error: --today expects YYYY-MM-DD, got {args.today!r}", file=sys.stderr)
            return 2
    else:
        today_d = date.today()
    today = today_d.isoformat()

    try:
        sources = load_config(Path(args.config))
    except (OSError, ValueError) as exc:
        print(f"error: cannot load config {args.config}: {exc}", file=sys.stderr)
        return 2
    if not sources:
        print(f"error: {args.config} lists no sources", file=sys.stderr)
        return 2

    demand_path = Path(args.demand)
    try:
        existing_demand = _read_existing_demand_or_empty(demand_path)
        existing_archive = _read_existing_demand_or_empty(Path(args.demand_archive))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    known_keys: set[str] = set()
    for r in existing_demand + existing_archive:
        known_keys |= match_keys(r)

    if args.fixture:
        with open(args.fixture, "r", encoding="utf-8") as fh:
            fixture_records = json.load(fh)
        sources = [dict(sources[0], _fixture=fixture_records)]

    all_new: list[dict] = []
    all_rejected: list[dict] = []
    failures: list[tuple[str, str]] = []
    for src in sources:
        source = src["source"]
        adapter = (src.get("adapter") or "socrata").lower()
        lookback = args.since_days if args.since_days is not None else \
            int(src.get("lookback_days") or DEFAULT_LOOKBACK_DAYS)
        since = (today_d - timedelta(days=lookback)).isoformat()
        try:
            if "_fixture" in src:
                records = src["_fixture"]
                if not isinstance(records, list):
                    raise ValueError("fixture must be a JSON array of permit records")
            elif adapter == "socrata":
                url = build_socrata_url(src, since)
                records = fetch_json(url)
                if src.get("limit") and len(records) >= int(src["limit"]):
                    print(f"::warning::{source}: hit $limit={src['limit']}; "
                          f"raise limit or shorten lookback")
            else:
                raise ValueError(f"adapter {adapter!r} not implemented (only 'socrata')")
        except (OSError, ValueError) as exc:
            msg = _error_message(exc)
            failures.append((source, msg))
            print(f"::warning::permit source FAILED: {source}: {msg}")
            print(f"error: {source}: {msg}", file=sys.stderr)
            continue

        result = ingest_source(records, src, today, known_keys)
        all_new.extend(result["accepted"])
        all_rejected.extend(result["rejected"])
        n_rej = len(result["rejected"]) - result["duplicates"]
        print(f"[{source}] since {since}: fetched {result['fetched']}, "
              f"grouped {result['grouped']}, accepted {len(result['accepted'])}, "
              f"rejected {n_rej}, duplicate {result['duplicates']}")
        if n_rej:
            by_reason: dict[str, int] = {}
            for r in result["rejected"]:
                if r["reason"] != "duplicate":
                    by_reason[r["reason"]] = by_reason.get(r["reason"], 0) + 1
            print("    rejected by reason: " + ", ".join(
                f"{k} x{v}" for k, v in sorted(by_reason.items(), key=lambda kv: (-kv[1], kv[0]))))

    for row in all_new:
        print(f"  + {row['demand_id']} | {row['facility_name']} | "
              f"buy-window {row['est_buy_window'] or '?'}")

    rc = 1 if failures else 0
    if failures:
        print(f"permit sources FAILED: {len(failures)}/{len(sources)}: "
              + "; ".join(f"{s}: {m}" for s, m in failures))

    if args.dry_run:
        print("dry run, nothing written")
        return rc

    if args.reject_log and all_rejected:
        append_reject_log(Path(args.reject_log), all_rejected)
        print(f"logged {len(all_rejected)} rejected/duplicate permit(s) to {args.reject_log}")

    if all_new:
        demand_radar.write_demand_rows_atomic(demand_path, existing_demand + all_new)
        print(f"wrote {len(all_new)} demand signal(s) to {demand_path}")
    else:
        print("(no new rows to write)")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
