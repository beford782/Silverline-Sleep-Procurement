#!/usr/bin/env python3
"""
ingest_rss.py — turn RSS/Atom feeds into filtered pipeline rows.

A generic feed adapter: point it at any RSS 2.0 or Atom feed and each entry
is mapped onto the pipeline schema, gated by the central mattress-relevance
filter (tools/relevance.py), deduped, and written as a `watching` row. This
is the compliant, no-scraping way to pull in:

  - Google Alerts (private / open-web "mattress RFP" chatter) — Atom feeds
    you create once in the Google Alerts UI ("Deliver to: RSS feed").
  - Bonfire per-portal open-opportunity feeds: https://{agency}.bonfirehub.com/opportunities/rss
  - RFPMart and any other portal/aggregator that publishes a real feed.

Bid submission stays manual; this only adds rows for a human to triage.

Feeds are supplied either with repeatable --feed/--source pairs or a JSON
config (see configs/feeds.example.json). Stdlib only (urllib + xml.etree).

Usage:
    # offline / test
    python tools/ingest_rss.py --fixture tests/fixtures/rss_sample.xml --source "Google Alerts" --dry-run
    # live: one feed
    python tools/ingest_rss.py --feed https://harriscounty.bonfirehub.com/opportunities/rss --source "Bonfire: Harris County"
    # live: many feeds from a config
    python tools/ingest_rss.py --feeds-config configs/feeds.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ACTIVE = REPO_ROOT / "bids" / "active" / "_pipeline.csv"
DEFAULT_ARCHIVE = REPO_ROOT / "bids" / "archive" / "_pipeline_archive.csv"
DEFAULT_TIMEOUT_S = 30

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import (  # noqa: E402
    CANONICAL_HEADER,
    read_rows,
    write_rows_atomic,
    slugify,
)
import relevance  # noqa: E402
import lead_radar  # noqa: E402
import demand_signal  # noqa: E402
import demand_radar  # noqa: E402


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _find_child(elem: ET.Element, name: str) -> ET.Element | None:
    for child in elem:
        if _localname(child.tag) == name:
            return child
    return None


def _child_text(elem: ET.Element, name: str) -> str:
    c = _find_child(elem, name)
    return (c.text or "").strip() if c is not None and c.text else ""


def _extract_link(entry: ET.Element) -> str:
    """RSS <link>text</link> or Atom <link href=.. rel=alternate>."""
    alt = ""
    first = ""
    for child in entry:
        if _localname(child.tag) != "link":
            continue
        href = child.get("href")
        if href:  # Atom
            rel = (child.get("rel") or "alternate").lower()
            if rel == "alternate" and not alt:
                alt = href
            if not first:
                first = href
        elif child.text and child.text.strip():  # RSS
            return child.text.strip()
    return (alt or first).strip()


def unwrap_google_redirect(url: str) -> str:
    """Google Alerts wraps targets as google.com/url?...&url=REAL — unwrap it."""
    if "google.com/url" not in url:
        return url
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    except ValueError:
        return url
    return (q.get("url") or q.get("q") or [url])[0]


def _normalize_date(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    # Atom ISO-8601
    try:
        return datetime.fromisoformat(v.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass
    # RSS RFC-822
    try:
        dt = parsedate_to_datetime(v)
        if dt is not None:
            return dt.date().isoformat()
    except (TypeError, ValueError):
        pass
    return v[:10] if len(v) >= 10 else ""


def parse_feed(xml_text: str) -> list[dict]:
    """Parse RSS 2.0 or Atom into a list of {title,url,date,summary} dicts."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ValueError(f"not valid XML: {exc}") from exc

    # RSS: rss/channel/item ; Atom: feed/entry
    items: list[ET.Element] = []
    channel = _find_child(root, "channel")
    container = channel if channel is not None else root
    for child in container:
        if _localname(child.tag) in ("item", "entry"):
            items.append(child)

    out: list[dict] = []
    for it in items:
        title = _child_text(it, "title")
        url = unwrap_google_redirect(_extract_link(it))
        date = (_child_text(it, "pubdate") or _child_text(it, "published")
                or _child_text(it, "updated") or _child_text(it, "date"))
        summary = (_child_text(it, "description") or _child_text(it, "summary")
                   or _child_text(it, "content"))
        if not title and not summary:
            continue
        out.append({"title": title, "url": url,
                    "date": _normalize_date(date), "summary": summary})
    return out


def entry_to_row(entry: dict, source: str, today: str) -> dict:
    title = (entry.get("title") or "").strip()
    url = (entry.get("url") or "").strip()
    summary = entry.get("summary") or ""
    basis = (url or title).encode("utf-8")
    short = hashlib.sha1(basis).hexdigest()[:6]
    oid = re.sub(r"-+", "-", "-".join(p for p in (slugify(source), slugify(title)) if p)).strip("-")[:110]
    oid = f"{oid}-{short}"
    row = {k: "" for k in CANONICAL_HEADER}
    row.update({
        "opportunity_id": oid,
        "status": "watching",
        "source": source,
        "title": title,
        "portal_url": url,
        "posted_date": entry.get("date") or today,
        "next_action": "Triage: verify source details, confirm specs, then decide bid/no-bid",
        "created_date": today,
        "last_reviewed": today,
        "notes": f"Auto-ingested from {source} feed; verify details at the source",
        "procurement_risk": "medium",
        "gate_status": "triage",
        "compliance_blocker": "source_verification_pending; specs_pending",
    })
    return row


# Hosts that are never real solicitations — news Q&A, social, retail.
NOISE_HOSTS = (
    "quora.com", "reddit.com", "wikipedia.org", "pinterest.com",
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "amazon.com", "ebay.com", "etsy.com", "walmart.com", "alibaba.com",
)


def _is_noise_host(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return any(host == h or host.endswith("." + h) for h in NOISE_HOSTS)


def existing_ids(rows: list[dict]) -> set[str]:
    return {(r.get("opportunity_id") or "").strip() for r in rows if r.get("opportunity_id")}


def ingest(entries: list[tuple], existing_rows: list[dict], today: str,
           home_states: frozenset[str] = relevance.HOME_STATES_DEFAULT,
           existing_leads: list[dict] | None = None,
           review_target: str = "leads",
           existing_lead_archive: list[dict] | None = None,
           existing_demand: list[dict] | None = None,
           existing_demand_archive: list[dict] | None = None,
           ) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Partition entries into (new_rows, leads, demand, dupes, rejected).

    Each entry is either a ``(entry, source)`` pair (kind defaults to
    'procurement') or a ``(entry, source, kind)`` triple. Procurement entries
    keep the legacy behavior: ACCEPT rows write to the active pipeline
    (new_rows); REVIEW rows route per `review_target` (default 'leads' ->
    Lead Radar; 'active' keeps the legacy HUMAN-flagged watching row;
    'reject-log' drops them); REJECT is unchanged. Lead dedup also consults the
    Lead Radar archive so a human-triaged dead lead is not re-ingested.

    Demand entries (kind == 'demand') run the pre-RFP demand classifier
    (demand_signal.classify_demand) and route ACCEPT/REVIEW signals to a
    parallel `demand` bucket (Demand Radar rows), deduped against both the
    Demand Radar review file and its archive. REJECT demand items are dropped
    (and collected in `rejected` so a reject-log can capture them).
    """
    existing_leads = existing_leads or []
    ids = existing_ids(existing_rows)
    lead_ids: set[str] = set()
    for r in existing_leads:
        lead_ids |= lead_radar.lead_match_keys(r)
    for r in (existing_lead_archive or []):
        lead_ids |= lead_radar.lead_match_keys(r)
    for r in existing_rows:
        lead_ids |= lead_radar.lead_match_keys(r)

    demand_ids: set[str] = set()
    for r in (existing_demand or []):
        demand_ids |= demand_radar.demand_match_keys(r)
    for r in (existing_demand_archive or []):
        demand_ids |= demand_radar.demand_match_keys(r)

    seen: set[str] = set()
    lead_seen: set[str] = set()
    demand_seen: set[str] = set()
    new_rows: list[dict] = []
    leads: list[dict] = []
    demand: list[dict] = []
    dupes: list[dict] = []
    rejected: list[dict] = []
    for item in entries:
        if len(item) == 3:
            entry, source, kind = item
        else:
            entry, source = item
            kind = "procurement"

        if kind == "demand":
            # Pre-RFP demand path: parallel to procurement, never touches the
            # bid pipeline. Mirror the noise-host rejection and reject-logging.
            title = (entry.get("title") or "").strip()
            link = (entry.get("url") or "").strip()
            text = "\n".join(p for p in (title, entry.get("summary", "")) if p)
            verdict = demand_signal.classify_demand(text, source=source)
            decision = verdict.decision
            if decision != "REJECT" and _is_noise_host(link):
                decision = "REJECT"
            if decision == "REJECT":
                rej = entry_to_row(entry, source, today)
                rej["notes"] = (f"{rej['notes']}; demand={decision}").strip("; ")
                rejected.append(rej)
                continue
            drow = demand_radar.build_demand_row(title, source, verdict, today,
                                                 source_url=link)
            keys = demand_radar.demand_match_keys(drow)
            if keys & demand_ids or keys & demand_seen:
                dupes.append(drow)
                continue
            demand_seen |= keys
            demand.append(drow)
            continue

        row = entry_to_row(entry, source, today)
        text = "\n".join(p for p in (row["title"], entry.get("summary", "")) if p)
        # Web/RSS items must carry a procurement cue to ACCEPT (filters news,
        # competitor catalogs); known junk hosts (Quora/Reddit/retail) are
        # rejected outright.
        verdict = relevance.classify(text, source=source, home_states=home_states,
                                     require_procurement=True)
        row["fit_score"] = str(verdict.confidence)
        decision = verdict.decision
        reasons = verdict.reasons
        if decision != "REJECT" and _is_noise_host(row["portal_url"]):
            decision = "REJECT"
            reasons = ["non-procurement source host"]
        row["notes"] = (f"{row['notes']}; relevance={decision}").strip("; ")
        if decision == "REJECT":
            row["next_action"] = "; ".join(reasons[:2])
            rejected.append(row)
            continue
        if decision == "REVIEW":
            if review_target == "reject-log":
                row["next_action"] = "HUMAN: confirm mattress scope — " + "; ".join(reasons[:2])
                rejected.append(row)
                continue
            if review_target == "leads":
                lead = lead_radar.build_lead_row(row, verdict, today)
                keys = lead_radar.lead_match_keys(lead)
                if keys & lead_ids or keys & lead_seen:
                    dupes.append(row)
                    continue
                lead_seen |= keys
                leads.append(lead)
                continue
            # review_target == "active": legacy fall-through to active pipeline.
            row["next_action"] = "HUMAN: confirm mattress scope — " + "; ".join(reasons[:2])
        oid = row["opportunity_id"]
        if oid in ids or oid in seen:
            dupes.append(row)
            continue
        seen.add(oid)
        new_rows.append(row)
    return new_rows, leads, demand, dupes, rejected


def fetch_feed(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> str:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "silverline-sleep-procurement/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _load_feeds(args) -> list[tuple[str, str, str]]:
    """Return list of (url, source, kind). `kind` is 'procurement' (default)
    or 'demand'; config entries may carry an optional "kind" key, while
    --feed URLs take their kind from the --kind flag."""
    feeds: list[tuple[str, str, str]] = []
    if args.feeds_config:
        with open(args.feeds_config, "r", encoding="utf-8") as fh:
            for f in json.load(fh):
                feeds.append((f["url"], f.get("source") or f["url"],
                              f.get("kind", "procurement")))
    for url in args.feed or []:
        feeds.append((url, args.source or url, getattr(args, "kind", "procurement")))
    return feeds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--feed", action="append", help="Feed URL (repeatable).")
    parser.add_argument("--source", default=None, help="Source label for --feed URLs.")
    parser.add_argument("--feeds-config", default=None, help="JSON list of {url, source, kind} feeds.")
    parser.add_argument("--fixture", default=None, help="Read one feed's XML from a file (testing).")
    parser.add_argument("--kind", choices=("procurement", "demand"), default="procurement",
                        help="Feed kind for --feed/--fixture manual paths (default: procurement). "
                             "'demand' routes entries through the pre-RFP demand classifier "
                             "into Demand Radar. Per-feed 'kind' in --feeds-config overrides this.")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE))
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--leads", default=str(lead_radar.DEFAULT_REVIEW),
                        help="Lead Radar CSV write target for REVIEW rows (default: %(default)s)")
    parser.add_argument("--lead-archive", default=str(lead_radar.DEFAULT_ARCHIVE),
                        help="Lead Radar archive consulted for dedup only; never written (default: %(default)s)")
    parser.add_argument("--demand", default=str(demand_radar.DEFAULT_REVIEW),
                        help="Demand Radar CSV write target for kind=demand signals (default: %(default)s)")
    parser.add_argument("--demand-archive", default=str(demand_radar.DEFAULT_ARCHIVE),
                        help="Demand Radar archive consulted for dedup only; never written (default: %(default)s)")
    parser.add_argument("--review-target", choices=("leads", "active", "reject-log"), default="leads",
                        help="Where REVIEW-band items go: 'leads' (Lead Radar, default), "
                             "'active' (legacy), or 'reject-log'.")
    parser.add_argument("--reject-log", default=None, help="Optional CSV path to append rejected rows.")
    parser.add_argument(
        "--allow-feed-failures",
        action="store_true",
        help=(
            "Exit 0 even when one or more feeds fail to fetch/parse. Default behavior "
            "exits non-zero on ANY feed failure so a swallowed 403/timeout/renamed "
            "feed (the silent-miss mode) trips the workflow's failure alert."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; do not write.")
    args = parser.parse_args(argv)

    today = datetime.now().date().isoformat()
    active_path = Path(args.active)
    archive_path = Path(args.archive)
    leads_path = Path(args.leads)
    demand_path = Path(args.demand)
    existing_active = _read_existing_or_empty(active_path)
    existing_rows = existing_active + _read_existing_or_empty(archive_path)
    existing_leads = _read_existing_leads_or_empty(leads_path)
    existing_lead_archive = _read_existing_leads_or_empty(Path(args.lead_archive))
    existing_demand = _read_existing_demand_or_empty(demand_path)
    existing_demand_archive = _read_existing_demand_or_empty(Path(args.demand_archive))

    entries: list[tuple] = []
    feeds_total = 0
    feeds_ok = 0
    feed_failures: list[tuple[str, str]] = []
    if args.fixture:
        with open(args.fixture, "r", encoding="utf-8") as fh:
            for e in parse_feed(fh.read()):
                entries.append((e, args.source or "RSS", args.kind))
    else:
        feeds = _load_feeds(args)
        if not feeds:
            print("error: provide --feed/--source, --feeds-config, or --fixture", file=sys.stderr)
            return 2
        feeds_total = len(feeds)
        for url, source, kind in feeds:
            # A fetch failure (403, timeout, renamed subdomain) or unparseable
            # body is the SILENT-MISS mode: left swallowed it produces zero rows
            # and a green run. Account for every failure and surface it (per-feed
            # ::warning:: + a structured summary), then exit non-zero below.
            try:
                xml_text = fetch_feed(url)
            except (urllib.error.HTTPError, urllib.error.URLError) as exc:
                msg = _feed_error_message(exc)
                feed_failures.append((source, msg))
                print(f"::warning::RSS feed FAILED: {source} ({url}): {msg}")
                print(f"warn: skipping {source} ({url}): {exc}", file=sys.stderr)
                continue
            try:
                parsed = parse_feed(xml_text)
            except ValueError as exc:
                feed_failures.append((source, str(exc)))
                print(f"::warning::RSS feed UNPARSEABLE: {source} ({url}): {exc}")
                print(f"warn: {source}: {exc}", file=sys.stderr)
                continue
            feeds_ok += 1
            for e in parsed:
                entries.append((e, source, kind))

    new_rows, leads, demand, dupes, rejected = ingest(
        entries, existing_rows, today, existing_leads=existing_leads,
        review_target=args.review_target,
        existing_lead_archive=existing_lead_archive,
        existing_demand=existing_demand,
        existing_demand_archive=existing_demand_archive)
    if not args.fixture:
        failed_desc = ", ".join(f"{s}: {e}" for s, e in feed_failures)
        print(f"feeds: {feeds_total} total, {feeds_ok} ok, "
              f"{len(feed_failures)} FAILED: [{failed_desc}]")
    feed_fail_rc = 1 if (feed_failures and not args.allow_feed_failures) else 0
    print(f"feed entries fetched: {len(entries)}")
    print(f"  active:   {len(new_rows)}")
    print(f"  leads:    {len(leads)} (review -> {args.review_target})")
    print(f"  demand:   {len(demand)} (pre-RFP -> Demand Radar)")
    print(f"  dupes:    {len(dupes)}")
    print(f"  rejected: {len(rejected)} (not mattress-relevant)")
    for r in new_rows:
        print(f"  + [{r['source']}] {r['title']}")
    for lead in leads:
        print(f"  ~ [lead/{lead['lead_type']}] {lead['title']}")
    for d in demand:
        print(f"  ~ [demand/{d.get('segment') or '?'}] {d.get('facility_name')}")

    if args.reject_log and rejected:
        _append_reject_log(Path(args.reject_log), rejected)
        print(f"  logged {len(rejected)} rejected row(s) to {args.reject_log}")

    if args.dry_run:
        print("(--dry-run: no files written)")
        return feed_fail_rc

    wrote_anything = False
    if new_rows:
        write_rows_atomic(active_path, existing_active + new_rows)
        print(f"wrote {len(new_rows)} active row(s) to {active_path}")
        wrote_anything = True
    if leads:
        lead_radar.write_lead_rows_atomic(leads_path, existing_leads + leads)
        print(f"wrote {len(leads)} lead(s) to {leads_path}")
        wrote_anything = True
    if demand:
        demand_radar.write_demand_rows_atomic(demand_path, existing_demand + demand)
        print(f"wrote {len(demand)} demand signal(s) to {demand_path}")
        wrote_anything = True
    if not wrote_anything:
        print("(no new rows to write)")
    return feed_fail_rc


def _feed_error_message(exc: Exception) -> str:
    """Compact, human-readable cause for a failed feed (e.g. 'HTTP 403')."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    reason = getattr(exc, "reason", None)
    return str(reason) if reason is not None else str(exc)


def _read_existing_or_empty(path: Path) -> list[dict]:
    if not path.exists():
        return []
    _, rows = read_rows(path)
    return rows


def _read_existing_leads_or_empty(path: Path) -> list[dict]:
    """Existing Lead Radar rows for dedup; empty when the file is absent."""
    if not path.exists():
        return []
    _, rows = lead_radar.read_lead_rows(path)
    return rows


def _read_existing_demand_or_empty(path: Path) -> list[dict]:
    """Existing Demand Radar rows for dedup; empty when the file is absent."""
    if not path.exists():
        return []
    _, rows = demand_radar.read_demand_rows(path)
    return rows


def _append_reject_log(path: Path, rejected: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANONICAL_HEADER, lineterminator="\n", extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rejected:
            writer.writerow(row)


if __name__ == "__main__":
    raise SystemExit(main())
