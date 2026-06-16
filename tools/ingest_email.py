#!/usr/bin/env python3
"""
ingest_email.py — turn portal commodity-alert emails into pipeline rows.

State/local and cooperative procurement portals (Bonfire, IonWave,
DemandStar, BidNet Direct, BuyBoard, Texas ESBD/CMBL, etc.) do NOT offer
public RSS feeds or documented opportunity APIs. The one compliant,
broadly-available channel is the commodity/NIGP-code email alert each
portal sends to a registered supplier. This tool reads those alert
emails (via the documented Gmail REST API, stdlib `urllib` only — NO
scraping, NO browser automation) and maps them onto the pipeline CSV,
exactly like tools/ingest_sam.py does for the SAM.gov federal API.

  email subject        -> title (alert-prefix stripped)
  sender domain        -> source (e.g. Bonfire, IonWave, DemandStar)
  first opportunity url -> portal_url
  "due/closes" date    -> due_date
  (best-effort regex)  -> buyer / delivery_location / solicitation_number

Bid submission stays manual. The tool only adds 'watching' rows for a
human to triage (read, score, decide bid/no-bid).

AUTHENTICATION (production / GitHub Action):
  Reads a Gmail mailbox using an OAuth2 refresh token, supplied via env:
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
  These are secrets — NEVER commit them. The mailbox identity is whatever
  account the refresh token was minted for, so this works against the
  business alert inbox without that account being "connected" anywhere
  else. See docs/email_ingest_setup.md for one-time provisioning.

TESTING / OFFLINE:
  --fixture FILE reads a JSON list of normalized messages instead of
  calling Gmail, so parsing/dedup/write are testable without credentials
  or network. Each message: {"id","sender","subject","date","body"}.

PARSER SCOPE:
  Alert-email layouts are vendor-specific and change over time. The
  bundled parser is a deliberately generic extractor (title + link + due
  date) that is honest about what it can read; richer per-sender fields
  should be added as real sample emails are captured (see SENDER_SOURCES
  and parse_message). It never invents data it cannot find.

Usage:
    # offline / test
    python tools/ingest_email.py --fixture tests/fixtures/email_alerts_sample.json --dry-run
    # live (creds in env)
    python tools/ingest_email.py --query 'label:Procurement/Alerts newer_than:8d'
"""

from __future__ import annotations

import argparse
import base64
import hashlib
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


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
DEFAULT_QUERY = "label:Procurement/Alerts newer_than:8d -in:trash -in:spam"
DEFAULT_MAX_MESSAGES = 200
DEFAULT_TIMEOUT_S = 30

# Map a sender-domain substring to a friendly pipeline `source` label.
# Order matters only for readability; matching is substring-against the
# message sender. Anything unmatched falls back to the bare domain.
SENDER_SOURCES: list[tuple[str, str]] = [
    # More specific subdomains/domains first so they win over generic ones
    # (e.g. region4esc.ionwave.net must match before bare "ionwave.net").
    ("region4esc", "Region 4 ESC (OMNIA)"),
    ("tips.ionwave.net", "TIPS"),
    ("tips-usa.com", "TIPS"),
    ("bonfirehub.com", "Bonfire"),
    ("gobonfire.com", "Bonfire"),
    ("ionwave.net", "IonWave"),
    ("demandstar.com", "DemandStar"),
    ("bidnetdirect.com", "BidNet Direct"),
    ("buyboard.com", "BuyBoard"),
    ("choicepartners.org", "Choice Partners"),
    ("hgacbuy.org", "HGACBuy"),
    ("opengov.com", "OpenGov (HGACBuy/other)"),
    ("sourcewell-mn.gov", "Sourcewell"),
    ("omniapartners.com", "OMNIA Partners"),
    ("txsmartbuy.gov", "Texas ESBD"),
    ("cpa.texas.gov", "Texas ESBD"),
    ("comptroller.texas.gov", "Texas ESBD"),
]

# Subject-line noise commonly prefixing the real solicitation title.
SUBJECT_PREFIXES = re.compile(
    r"^\s*(re:|fwd:|fw:|"
    r"(new\s+)?(bid|opportunity|solicitation|rfp|rfq|ifb|sourcing)\s*"
    r"(notification|notice|alert|invitation|matching[^:]*)?\s*[:\-–]\s*)+",
    re.IGNORECASE,
)

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)

# "due", "closes", "response due", "closing date" ... <date>
DUE_DATE_RE = re.compile(
    r"(?:due|clos(?:e|es|ing)|response\s+due|deadline|submit\s+by)"
    r"[^0-9A-Za-z]{0,20}"
    r"([A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}"
    r"|\d{1,2}/\d{1,2}/\d{2,4}"
    r"|\d{4}-\d{2}-\d{2})",
    re.IGNORECASE,
)

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%B %d %Y",
    "%B %d, %Y",
    "%b %d %Y",
    "%b %d, %Y",
)


# --------------------------------------------------------------------------
# Field extraction (generic, honest — never fabricates)
# --------------------------------------------------------------------------
def source_for_sender(sender: str) -> str:
    """Map an email sender to a friendly pipeline source label."""
    low = (sender or "").lower()
    for needle, label in SENDER_SOURCES:
        if needle in low:
            return label
    # Fall back to the bare domain, e.g. "bids@foo.gov" -> "foo.gov".
    m = re.search(r"@([^>\s]+)", low)
    return (m.group(1) if m else (low or "Email alert")).strip()


def clean_title(subject: str) -> str:
    """Strip common alert-notification prefixes from an email subject."""
    title = (subject or "").strip()
    prev = None
    # Apply repeatedly so "Fwd: New Bid Notification: X" fully unwraps.
    while title and title != prev:
        prev = title
        title = SUBJECT_PREFIXES.sub("", title).strip()
    return title or (subject or "").strip()


def normalize_date(value: str) -> str:
    """Parse a human/locale date string into YYYY-MM-DD, or '' if unknown."""
    v = (value or "").strip().replace(",", "")
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def extract_due_date(text: str) -> str:
    m = DUE_DATE_RE.search(text or "")
    return normalize_date(m.group(1)) if m else ""


_ADMIN_LINK_RE = re.compile(r"unsubscrib|preferenc|optout|opt-out|mailto|privacy|/help", re.IGNORECASE)


def extract_url(text: str, source_hint: str = "") -> str:
    """Pick the most relevant opportunity URL from the body.

    Prefer a link hosted on the sending platform's domain; otherwise the
    first link that is not an obvious unsubscribe/preferences/help link.
    """
    urls = [u.rstrip(".,);") for u in URL_RE.findall(text or "")]
    if not urls:
        return ""
    known_domains = [needle for needle, _ in SENDER_SOURCES]
    for u in urls:
        if any(d in u.lower() for d in known_domains):
            return u
    non_admin = [u for u in urls if not _ADMIN_LINK_RE.search(u)]
    return (non_admin or urls)[0]


def parse_message(msg: dict, today: str) -> dict | None:
    """Map one normalized email message to a pipeline row dict (or None).

    Returns None when the message carries no usable opportunity title.
    """
    subject = (msg.get("subject") or "").strip()
    body = msg.get("body") or ""
    sender = msg.get("sender") or ""
    source = source_for_sender(sender)
    title = clean_title(subject)
    if not title:
        return None

    url = extract_url(body, source)
    due_date = extract_due_date(subject + "\n" + body)
    posted = normalize_date((msg.get("date") or "")[:10]) or today

    # Stable id: source + title, disambiguated by a short hash of the url
    # (so two same-titled solicitations from one source don't collide, and
    # re-ingesting the same alert maps to the same id for dedup).
    basis = (url or title).encode("utf-8")
    short = hashlib.sha1(basis).hexdigest()[:6]
    parts = [slugify(source), slugify(title)]
    opportunity_id = re.sub(r"-+", "-", "-".join(p for p in parts if p)).strip("-")[:110]
    opportunity_id = f"{opportunity_id}-{short}"

    row = {k: "" for k in CANONICAL_HEADER}
    row.update({
        "opportunity_id": opportunity_id,
        "status": "watching",
        "source": source,
        "title": title,
        "portal_url": url,
        "posted_date": posted,
        "due_date": due_date,
        "next_action": "Triage: open portal link, run pipeline.py score, decide bid/no-bid",
        "created_date": today,
        "last_reviewed": today,
        "notes": f"Auto-ingested from {source} email alert; verify details on the portal",
    })
    return row


# --------------------------------------------------------------------------
# Dedup + ingest (mirrors ingest_sam.py)
# --------------------------------------------------------------------------
def existing_ids(rows: list[dict]) -> set[str]:
    return {(r.get("opportunity_id") or "").strip() for r in rows if r.get("opportunity_id")}


def ingest(messages: Iterable[dict], existing_rows: list[dict], today: str) -> tuple[list[dict], list[dict], list[dict]]:
    """Partition messages into (new_rows, dupes, skipped).

    dupes: rows whose opportunity_id is already tracked.
    skipped: messages that produced no usable row (no title).
    """
    ids = existing_ids(existing_rows)
    seen: set[str] = set()
    new_rows: list[dict] = []
    dupes: list[dict] = []
    skipped: list[dict] = []
    for msg in messages:
        row = parse_message(msg, today)
        if row is None:
            skipped.append(msg)
            continue
        oid = row["opportunity_id"]
        if oid in ids or oid in seen:
            dupes.append(row)
            continue
        seen.add(oid)
        new_rows.append(row)
    return new_rows, dupes, skipped


# --------------------------------------------------------------------------
# Gmail REST client (stdlib urllib; OAuth2 refresh-token flow)
# --------------------------------------------------------------------------
def _http_json(url: str, *, data: bytes | None = None, headers: dict | None = None,
               timeout: float = DEFAULT_TIMEOUT_S) -> dict:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Exchange a refresh token for a short-lived access token."""
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode("utf-8")
    payload = _http_json(
        GOOGLE_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("token endpoint returned no access_token")
    return token


def _decode_b64url(data: str) -> str:
    if not data:
        return ""
    pad = "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(data + pad).decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&nbsp;", " ")
                .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))
    return re.sub(r"[ \t]+", " ", text)


def _extract_body(payload: dict) -> str:
    """Walk a Gmail message payload tree; prefer text/plain, else text/html."""
    plains: list[str] = []
    htmls: list[str] = []

    def walk(part: dict) -> None:
        mime = part.get("mimeType") or ""
        body = part.get("body") or {}
        data = body.get("data")
        if data:
            decoded = _decode_b64url(data)
            if mime == "text/plain":
                plains.append(decoded)
            elif mime == "text/html":
                htmls.append(_strip_html(decoded))
        for child in part.get("parts") or []:
            walk(child)

    walk(payload or {})
    if plains:
        return "\n".join(plains)
    return "\n".join(htmls)


def _header(headers: list[dict], name: str) -> str:
    for h in headers or []:
        if (h.get("name") or "").lower() == name.lower():
            return h.get("value") or ""
    return ""


def fetch_messages(access_token: str, query: str, max_messages: int) -> list[dict]:
    """Fetch messages matching a Gmail search query; return normalized dicts."""
    auth = {"Authorization": f"Bearer {access_token}"}
    normalized: list[dict] = []
    page_token = None
    while len(normalized) < max_messages:
        params = {"q": query, "maxResults": str(min(100, max_messages - len(normalized)))}
        if page_token:
            params["pageToken"] = page_token
        listing = _http_json(f"{GMAIL_API_BASE}/messages?" + urllib.parse.urlencode(params), headers=auth)
        for ref in listing.get("messages") or []:
            full = _http_json(
                f"{GMAIL_API_BASE}/messages/{ref['id']}?format=full",
                headers=auth,
            )
            payload = full.get("payload") or {}
            headers = payload.get("headers") or []
            normalized.append({
                "id": full.get("id") or ref.get("id"),
                "sender": _header(headers, "From"),
                "subject": _header(headers, "Subject"),
                "date": _header(headers, "Date"),
                "body": _extract_body(payload),
            })
            if len(normalized) >= max_messages:
                break
        page_token = listing.get("nextPageToken")
        if not page_token:
            break
    return normalized


def _read_existing_or_empty(path: Path) -> list[dict]:
    if not path.exists():
        return []
    _, rows = read_rows(path)
    return rows


def _load_messages(args) -> list[dict]:
    if args.fixture:
        with open(args.fixture, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("fixture must be a JSON list of message objects")
        return data
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        raise SystemExit(
            "error: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN "
            "env vars are required for live ingest (or pass --fixture). "
            "See docs/email_ingest_setup.md. Never commit these secrets."
        )
    access_token = get_access_token(client_id, client_secret, refresh_token)
    return fetch_messages(access_token, args.query, args.max_messages)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help=f"Gmail search query for alert emails (default: {DEFAULT_QUERY!r})")
    parser.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES,
                        help=f"Safety cap on messages fetched (default {DEFAULT_MAX_MESSAGES}).")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE),
                        help=f"Pipeline CSV write target (default: {DEFAULT_ACTIVE.relative_to(REPO_ROOT)})")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE),
                        help=f"Archive CSV consulted for dedup only; never written. Default: {DEFAULT_ARCHIVE.relative_to(REPO_ROOT)}")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; do not write.")
    parser.add_argument("--fixture", default=None,
                        help="Read a JSON list of normalized messages instead of calling Gmail (testing).")
    args = parser.parse_args(argv)

    today = datetime.now().date().isoformat()
    active_path = Path(args.active)
    archive_path = Path(args.archive)
    existing_active = _read_existing_or_empty(active_path)
    existing_archive = _read_existing_or_empty(archive_path)
    existing_rows = existing_active + existing_archive

    messages = _load_messages(args)
    new_rows, dupes, skipped = ingest(messages, existing_rows, today)

    print(f"email alerts fetched: {len(messages)} message(s)")
    print(f"  new:     {len(new_rows)}")
    print(f"  dupes:   {len(dupes)}")
    print(f"  skipped: {len(skipped)} (no usable title)")
    for r in new_rows:
        print(f"  + [{r['source']}] {r['opportunity_id']} :: {r['title']}")

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0
    if not new_rows:
        print("(no new rows to write)")
        return 0

    write_rows_atomic(active_path, existing_active + new_rows)
    print(f"wrote {len(new_rows)} new row(s) to {active_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
