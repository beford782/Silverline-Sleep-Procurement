#!/usr/bin/env python3
"""
ingest_sam.py — pull federal opportunities from SAM.gov into the pipeline.

Uses the documented SAM.gov "Get Opportunities" public API
(https://api.sam.gov/opportunities/v2/search) — see the open.gsa.gov
docs for the full field list. We deliberately use only stdlib
(`urllib.request`, `json`, `csv`) so the toolkit stays dependency-free.

The script does NOT submit bids and does NOT pull personally identifiable
contact details from the API response. It maps the documented public
fields onto the pipeline CSV's columns:

  noticeId / solicitationNumber  -> opportunity_id (slugified)
  title                          -> title
  fullParentPathName / department-> buyer
  solicitationNumber             -> solicitation_number
  uiLink                         -> portal_url
  postedDate                     -> posted_date
  responseDeadLine               -> due_date
  placeOfPerformance             -> delivery_location
  naicsCode / classificationCode -> commodity_terms
  type                           -> notes (e.g. "Sources Sought")

The API key is read from the SAM_API_KEY environment variable or the
--api-key flag. Sign up for a free key at sam.gov (Profile → Account
Details → API Key). NEVER commit the key.

Usage:
    SAM_API_KEY=... python tools/ingest_sam.py \
        --title "mattress" \
        --posted-from 2026-05-01 \
        --posted-to 2026-05-14 \
        [--limit 50] [--dry-run] [--active PATH]

The SAM.gov API uses HTTP 404 (with "No Data found" semantics) when
zero opportunities match — this script handles that as a normal
empty-result case rather than an error.
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
from datetime import datetime
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"

# Make pipeline helpers reusable without duplication.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import (  # noqa: E402
    CANONICAL_HEADER,
    read_rows,
    write_rows_atomic,
    slugify,
)
import relevance  # noqa: E402


SAM_SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
DEFAULT_LIMIT = 50
DEFAULT_TIMEOUT_S = 30


def _empty_payload(limit: int, offset: int) -> dict:
    return {
        "totalRecords": 0,
        "limit": limit,
        "offset": offset,
        "opportunitiesData": [],
    }


def _parse_iso_date(value: str) -> str:
    """Accept YYYY-MM-DD and pass through."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"date must be YYYY-MM-DD ({exc})"
        ) from exc


def _iso_to_sam_date(iso: str) -> str:
    """SAM.gov v2 search expects MM/dd/yyyy in query params."""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%m/%d/%Y")


def build_search_url(
    api_key: str,
    posted_from: str,
    posted_to: str,
    title: str | None = None,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    naics_code: str | None = None,
    notice_type: str | None = None,
    classification_code: str | None = None,
    response_deadline_after: str | None = None,
    response_deadline_before: str | None = None,
) -> str:
    """Compose the SAM.gov search URL with safely encoded params.

    Parameter names match the documented SAM.gov v2 search API: `title`,
    `ncode`, `ccode`, `ptype`, `rdlfrom`, `rdlto`. There is no documented
    free-text keyword param; use `title` for keyword-style matching
    against opportunity titles, or `ccode` (PSC) / `ncode` (NAICS) to
    sweep by procurement classification regardless of title wording.
    """
    params: dict[str, str] = {
        "api_key": api_key,
        "postedFrom": _iso_to_sam_date(posted_from),
        "postedTo": _iso_to_sam_date(posted_to),
        "limit": str(limit),
        "offset": str(offset),
    }
    if title:
        params["title"] = title
    if naics_code:
        # Docs use `ncode` for the request parameter despite the response
        # field being `naicsCode`. Both names are accepted by the API;
        # we use the documented request-side name.
        params["ncode"] = naics_code
    if classification_code:
        # SAM.gov v2 uses `ccode` for the PSC / classification code on the
        # request side (the response field is `classificationCode`).
        params["ccode"] = classification_code
    if notice_type:
        params["ptype"] = notice_type
    if response_deadline_after:
        params["rdlfrom"] = _iso_to_sam_date(response_deadline_after)
    if response_deadline_before:
        params["rdlto"] = _iso_to_sam_date(response_deadline_before)
    return SAM_SEARCH_URL + "?" + urllib.parse.urlencode(params)


def fetch_page(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    """GET the URL and return parsed JSON. Stdlib-only HTTP client."""
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "silverline-sleep-procurement/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        body = resp.read()
    return json.loads(body.decode("utf-8"))


def _extract_place_of_performance(pop: dict | None) -> str:
    if not pop:
        return ""
    city = (pop.get("city") or {}).get("name") or ""
    state = (pop.get("state") or {}).get("code") or (pop.get("state") or {}).get("name") or ""
    return ", ".join(p for p in (city, state) if p)


def _extract_commodity_terms(record: dict) -> str:
    """Join NAICS + classification codes into the pipeline's '; '-separated convention."""
    parts: list[str] = []
    naics = record.get("naicsCode") or ""
    classification = record.get("classificationCode") or ""
    if naics:
        parts.append(f"NAICS {naics}")
    if classification:
        parts.append(f"PSC {classification}")
    return "; ".join(parts)


def _extract_buyer(record: dict) -> str:
    """Prefer the deepest agency name. Fall back to department/office."""
    candidates = (
        record.get("fullParentPathName"),
        record.get("department"),
        record.get("subTier"),
        record.get("office"),
    )
    for c in candidates:
        if c:
            return c.replace(".", " ").strip()
    return ""


def _normalize_due_date(value: str) -> str:
    """SAM returns ISO 8601 with a timezone; pipeline wants YYYY-MM-DD."""
    if not value:
        return ""
    # Common SAM format: '2026-06-15T17:00:00-04:00' or '2026-06-15'.
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        # Fall back to a date-only prefix when fromisoformat can't parse.
        return value[:10] if len(value) >= 10 else value


def _normalize_posted_date(value: str) -> str:
    """SAM postedDate is typically already YYYY-MM-DD; normalize defensively."""
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).date().isoformat()
    except ValueError:
        return value[:10] if len(value) >= 10 else value


def record_to_row(record: dict, today: str) -> dict:
    """Map a SAM.gov opportunity record onto a pipeline CSV row dict."""
    solicitation_number = (record.get("solicitationNumber") or "").strip()
    notice_id = (record.get("noticeId") or "").strip()
    title = (record.get("title") or "").strip()
    buyer = _extract_buyer(record)
    # Stable opportunity id: prefer slugified solicitation_number; else noticeId.
    label = solicitation_number or notice_id or title
    parts = [slugify("SAM.gov"), slugify(buyer), slugify(label)]
    opportunity_id = re.sub(r"-+", "-", "-".join(p for p in parts if p)).strip("-")[:120]

    row = {k: "" for k in CANONICAL_HEADER}
    row.update({
        "opportunity_id": opportunity_id,
        "status": "watching",
        "source": "SAM.gov",
        "buyer": buyer,
        "solicitation_number": solicitation_number,
        "title": title,
        "portal_url": (record.get("uiLink") or "").strip(),
        "posted_date": _normalize_posted_date(record.get("postedDate") or ""),
        "due_date": _normalize_due_date(record.get("responseDeadLine") or ""),
        "delivery_location": _extract_place_of_performance(record.get("placeOfPerformance")),
        "commodity_terms": _extract_commodity_terms(record),
        "next_action": (
            "Triage: clear procurement blockers, read solicitation attachments, "
            "confirm specs, then decide bid/no-bid"
        ),
        "created_date": today,
        "last_reviewed": today,
        "notes": (record.get("type") or "").strip(),
        "procurement_risk": "blocker",
        "gate_status": "blocked",
        "compliance_blocker": "sam_registration_pending; specs_pending",
    })
    return row


def existing_ids(rows: list[dict]) -> tuple[set[str], set[str]]:
    """Return (opportunity_ids, solicitation_numbers) already in the pipeline."""
    ids = {(r.get("opportunity_id") or "").strip() for r in rows if r.get("opportunity_id")}
    sols = {(r.get("solicitation_number") or "").strip() for r in rows if r.get("solicitation_number")}
    return ids, sols


def ingest(
    records: Iterable[dict],
    existing_rows: list[dict],
    today: str,
    home_states: frozenset[str] = relevance.HOME_STATES_DEFAULT,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition incoming records into (new_rows, dupes, rejected).

    Each record is gated by the central mattress-relevance classifier:
    REJECT records go to `rejected` (never written); REVIEW records are
    kept but flagged in next_action for human confirmation; ACCEPT records
    are kept normally. `dupes` are rows already in the pipeline by
    opportunity_id or solicitation_number.
    """
    ids, sols = existing_ids(existing_rows)
    new_rows: list[dict] = []
    dupes: list[dict] = []
    rejected: list[dict] = []
    for record in records:
        row = record_to_row(record, today)
        text = "\n".join(p for p in (row["title"], row["commodity_terms"],
                                     row["delivery_location"]) if p)
        verdict = relevance.classify(text, buyer=row["buyer"], source="SAM.gov",
                                     home_states=home_states)
        row["fit_score"] = str(verdict.confidence)
        if verdict.decision == "REJECT":
            row["next_action"] = "; ".join(verdict.reasons[:2])
            rejected.append(row)
            continue
        if verdict.decision == "REVIEW":
            row["next_action"] = "HUMAN: confirm mattress scope — " + "; ".join(verdict.reasons[:2])
        sol_no = row["solicitation_number"]
        if row["opportunity_id"] in ids or (sol_no and sol_no in sols):
            dupes.append(row)
            continue
        ids.add(row["opportunity_id"])
        if sol_no:
            sols.add(sol_no)
        new_rows.append(row)
    return new_rows, dupes, rejected


def _read_existing_or_empty(active_path: Path) -> list[dict]:
    if not active_path.exists():
        return []
    _, rows = read_rows(active_path)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--title", default=None, help="Match opportunity title (SAM.gov 'title' parameter; substring match)")
    parser.add_argument("--posted-from", required=True, type=_parse_iso_date, help="YYYY-MM-DD (inclusive); max 1-year range per SAM.gov")
    parser.add_argument("--posted-to", required=True, type=_parse_iso_date, help="YYYY-MM-DD (inclusive); max 1-year range per SAM.gov")
    parser.add_argument("--naics-code", default=None, help="NAICS code, e.g. 337910 for mattress manufacturing (sent as 'ncode')")
    parser.add_argument("--psc", default=None, help="PSC / classification code, e.g. 7210 (household furnishings) or 7105 (household furniture) (sent as 'ccode')")
    parser.add_argument("--notice-type", default=None, help="Procurement type code: o=Solicitation, k=Combined Synopsis/Solicitation, r=Sources Sought, p=Pre-solicitation, a=Award, etc. (sent as 'ptype')")
    parser.add_argument("--response-deadline-after", type=_parse_iso_date, default=None,
                        help="Filter to opportunities with response deadline on or after YYYY-MM-DD (sent as 'rdlfrom'). "
                             "Default: today, so past-due opportunities are excluded.")
    parser.add_argument("--response-deadline-before", type=_parse_iso_date, default=None,
                        help="Filter to opportunities with response deadline on or before YYYY-MM-DD (sent as 'rdlto'). "
                             "Max 1-year range when combined with --response-deadline-after.")
    parser.add_argument("--include-past-due", action="store_true",
                        help="Opt out of the default 'rdlfrom=today' filter so past-due opportunities are also returned. "
                             "Ignored if --response-deadline-after is given.")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"Page size (default {DEFAULT_LIMIT}, SAM max 1000).")
    parser.add_argument("--max-pages", type=int, default=10, help="Stop after this many pages (safety cap).")
    parser.add_argument("--api-key", default=None, help="Override SAM_API_KEY env var.")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help=f"Pipeline CSV write target (default: {DEFAULT_ACTIVE.relative_to(REPO_ROOT)})")
    parser.add_argument(
        "--archive",
        default=str(DEFAULT_ARCHIVE),
        help=(
            f"Archive pipeline CSV consulted for dedup only; never written. "
            f"Default: {DEFAULT_ARCHIVE.relative_to(REPO_ROOT)}"
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; do not write.")
    parser.add_argument("--fixture", default=None, help="Read response JSON from a file instead of the live API (testing).")
    parser.add_argument(
        "--allow-throttled-empty",
        action="store_true",
        help=(
            "Treat SAM.gov HTTP 429 quota throttling as an empty result and exit 0. "
            "Use this for unattended scheduled runs; default behavior still fails."
        ),
    )
    args = parser.parse_args(argv)

    today = datetime.now().date().isoformat()
    active_path = Path(args.active)
    archive_path = Path(args.archive)
    existing_active = _read_existing_or_empty(active_path)
    existing_archive = _read_existing_or_empty(archive_path)
    # Dedup against both pipelines so previously-closed opportunities (e.g.
    # archived no-bids) do not get re-ingested into the active pipeline.
    existing_rows = existing_active + existing_archive

    if args.fixture:
        with open(args.fixture, "r", encoding="utf-8") as fh:
            payloads = [json.load(fh)]
    else:
        api_key = args.api_key or os.environ.get("SAM_API_KEY")
        if not api_key:
            print(
                "error: SAM_API_KEY env var is required (or pass --api-key). "
                "Get a free key from sam.gov: Profile -> Account Details -> API Key. "
                "Never commit the key.",
                file=sys.stderr,
            )
            return 2

        # Default: exclude past-due opportunities. Operator can pin a
        # different rdlfrom explicitly, or opt out with --include-past-due.
        if args.response_deadline_after:
            rdl_after = args.response_deadline_after
        elif args.include_past_due:
            rdl_after = None
        else:
            rdl_after = today

        payloads = []
        offset = 0
        for page in range(args.max_pages):
            url = build_search_url(
                api_key=api_key,
                posted_from=args.posted_from,
                posted_to=args.posted_to,
                title=args.title,
                limit=args.limit,
                offset=offset,
                naics_code=args.naics_code,
                notice_type=args.notice_type,
                classification_code=args.psc,
                response_deadline_after=rdl_after,
                response_deadline_before=args.response_deadline_before,
            )
            try:
                payload = fetch_page(url)
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")[:500]
                if exc.code == 404:
                    # SAM.gov returns 404 with "No Data found" semantics
                    # per its public docs; treat as zero results, not as
                    # an error.
                    payload = _empty_payload(args.limit, offset)
                elif exc.code == 429 and args.allow_throttled_empty:
                    print(
                        f"warning: HTTP 429 from SAM.gov; treating as empty scheduled result: {body}",
                        file=sys.stderr,
                    )
                    payload = _empty_payload(args.limit, offset)
                else:
                    print(f"error: HTTP {exc.code} from SAM.gov: {body}", file=sys.stderr)
                    return 1
            except urllib.error.URLError as exc:
                print(f"error: network error contacting SAM.gov: {exc}", file=sys.stderr)
                return 1
            except json.JSONDecodeError as exc:
                print(f"error: SAM.gov returned non-JSON: {exc}", file=sys.stderr)
                return 1
            payloads.append(payload)
            records_on_page = payload.get("opportunitiesData") or []
            total = payload.get("totalRecords") or 0
            offset += len(records_on_page)
            if not records_on_page or offset >= total:
                break

    records: list[dict] = []
    for payload in payloads:
        records.extend(payload.get("opportunitiesData") or [])

    new_rows, dupes, rejected = ingest(records, existing_rows, today)

    # Attribute each dupe to active vs archive so the operator can tell
    # "already tracking it" from "previously closed, ignore."
    archive_ids, archive_sols = existing_ids(existing_archive)
    n_archive_dupes = sum(
        1
        for d in dupes
        if d["opportunity_id"] in archive_ids
        or (d.get("solicitation_number") and d["solicitation_number"] in archive_sols)
    )
    n_active_dupes = len(dupes) - n_archive_dupes

    print(f"SAM.gov fetched: {len(records)} record(s)")
    print(f"  new:    {len(new_rows)}")
    print(f"  dupes:  {len(dupes)} ({n_active_dupes} active, {n_archive_dupes} archive)")
    print(f"  rejected: {len(rejected)} (not mattress-relevant)")
    if new_rows:
        for r in new_rows:
            print(f"  + {r['opportunity_id']} :: {r['title']}")

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0
    if not new_rows:
        print("(no new rows to write)")
        return 0

    # Write target is active only; archive rows were consulted for dedup
    # but must never be echoed back into the active pipeline.
    write_rows_atomic(active_path, existing_active + new_rows)
    print(f"wrote {len(new_rows)} new row(s) to {active_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
