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
  --provider graph (DEFAULT) — read an Outlook / Microsoft 365 mailbox via
  the documented Microsoft Graph API, app-only (client-credentials) OAuth:
    GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET, GRAPH_MAILBOX
  GRAPH_MAILBOX is the target UPN (e.g. beford@silverlinesleep.com); the
  app needs the application permission Mail.Read (admin-consented).

  --provider gmail — read a Gmail mailbox via the Gmail REST API using an
  OAuth2 refresh token:
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

  --provider imap — read a Gmail (or any IMAP) mailbox over IMAP4-TLS using a
  self-issued app password. No Azure/Workspace admin, no OAuth consent screen,
  no token expiry — the most robust unattended path for a solo operator:
    GMAIL_ADDRESS, GMAIL_APP_PASSWORD
  Requires 2-Step Verification on the account and IMAP enabled in Gmail
  settings. Opens the mailbox read-only (never marks alerts seen).

  All of these are secrets — NEVER commit them. The mailbox identity comes
  from the credentials, so this works against the business alert inbox
  without that account being "connected" anywhere else. See
  docs/email_ingest_setup.md for one-time provisioning.

TESTING / OFFLINE:
  --fixture FILE reads a JSON list of normalized messages instead of
  calling any mail API, so parsing/dedup/write are testable without
  credentials or network. Each message: {"id","sender","subject","date","body"}.

PARSER SCOPE:
  Alert-email layouts are vendor-specific and change over time. The
  bundled parser is a deliberately generic extractor (title + link + due
  date) that is honest about what it can read; richer per-sender fields
  should be added as real sample emails are captured (see SENDER_SOURCES
  and parse_message). It never invents data it cannot find.

  One per-sender adapter ships: split_ionwave_digest() handles IonWave
  "Matching Bid Opportunities" alerts, which list several solicitations in
  one email. It splits them into one row per bid (real per-bid title +
  Bid Number -> solicitation_number + close date) instead of collapsing
  the digest to a single row titled with the generic email subject.

  Forwarded alerts are normalized first: when the operator's Outlook rule
  FORWARDS a portal alert (so the message sender is the forwarding mailbox and
  the original alert is quoted in the body), unwrap_forwarded() recovers the
  original portal sender/subject from the quoted "From:/Subject:" header so the
  alert parses exactly like a direct one. This runs on every provider path
  (Graph, Gmail, fixture), so the scheduled Graph run handles forwarded alerts
  the same way the manual sweep did by hand.

Usage:
    # offline / test
    python tools/ingest_email.py --fixture tests/fixtures/email_alerts_sample.json --dry-run
    # live Outlook/Graph (default provider; creds in env)
    python tools/ingest_email.py --graph-folder "Procurement Alerts" --since-days 8
    # live Gmail
    python tools/ingest_email.py --provider gmail --query 'label:Procurement/Alerts newer_than:8d'
"""

from __future__ import annotations

import argparse
import base64
import email
import hashlib
import imaplib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from email.header import decode_header, make_header
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
import lead_radar  # noqa: E402


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_QUERY = "label:Procurement/Alerts newer_than:8d -in:trash -in:spam"
DEFAULT_SINCE_DAYS = 8
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

# "due", "closes", "response due", "closing date" ... <date>. The optional
# " date" lets "Close Date: 6/5/2026" match (the literal word "Date" otherwise
# sits between the keyword and the value and breaks the gap match).
DUE_DATE_RE = re.compile(
    r"(?:due|clos(?:e|es|ing)|response\s+due|deadline|submit\s+by)"
    r"(?:\s+date)?"
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


# --------------------------------------------------------------------------
# Forwarded-alert normalization (provider-agnostic)
# --------------------------------------------------------------------------
# The operator setup (docs/email_ingest_setup.md, 2026-06-18) FORWARDS portal
# alerts from the Outlook business mailbox to a triage inbox. A forwarded alert
# carries the forwarding mailbox as its sender (e.g. beford@silverlinesleep.com)
# and quotes the ORIGINAL portal alert — including a "From:/Sent:/Subject:"
# header block — inside the body. Left as-is, source_for_sender() mislabels the
# source as the forwarder's domain and the per-sender adapters never fire (the
# IonWave splitter keys on "ionwave" in the sender). This recovers the original
# portal sender/subject from the quoted header so a forwarded alert parses
# identically to a direct one — the same recovery the manual Gmail sweep did by
# hand, now applied automatically on every provider path (Graph, Gmail, fixture).
#
# Conservative: only fires when the body contains a real forwarded header block
# (a "From:" line bearing an email address AND a following "Subject:" line), so
# direct portal alerts that merely mention "From:" in prose are left untouched.
_FWD_FROM_RE = re.compile(r"^[ \t>]*From:[ \t]*(?P<sender>.+?)[ \t]*$",
                          re.IGNORECASE | re.MULTILINE)
_FWD_SUBJECT_RE = re.compile(r"^[ \t>]*Subject:[ \t]*(?P<subject>.+?)[ \t]*$",
                             re.IGNORECASE | re.MULTILINE)


def unwrap_forwarded(msg: dict) -> dict:
    """Recover the original portal sender/subject from a forwarded alert body.

    Returns a shallow copy of `msg` with `sender` (and `subject`, when present)
    taken from the quoted forwarded header and `body` trimmed to the forwarded
    content. Returns `msg` unchanged when no forwarded header block is found.
    The message's own `date` is intentionally kept (the provider-normalized
    received date parses; the quoted human "Sent:" string does not).
    """
    body = msg.get("body") or ""
    mfrom = _FWD_FROM_RE.search(body)
    if not mfrom:
        return msg
    sender = mfrom.group("sender").strip()
    if "@" not in sender:  # a forwarded From: header always carries an address
        return msg
    tail = body[mfrom.start():]
    msubj = _FWD_SUBJECT_RE.search(tail)
    if not msubj:  # require a Subject: line to confirm a real header block
        return msg

    new = dict(msg)
    new["sender"] = sender
    subject = msubj.group("subject").strip()
    if subject:
        new["subject"] = subject
    new["body"] = tail
    return new


# --------------------------------------------------------------------------
# IonWave structured-digest adapter
# --------------------------------------------------------------------------
# IonWave portals (ESC eMarketplace, Region ESCs, TIPS, Choice Partners, ...)
# send "Matching Bid Opportunities" alerts that list 1+ solicitations as
# labeled blocks. A generic one-row-per-email parse collapses a multi-bid
# digest to a single row titled with the email subject ("Matching Bid
# Opportunities"), losing the real per-bid title, number, and close date.
# This adapter splits such an email into one normalized sub-message per bid,
# tolerating both the "Title:/Open Date:" (new-opportunity) and "Bid Title:/
# Issue Date:" (question-answered) label variants, and label-then-value laid
# out on one line or two (plain text vs. HTML-stripped tables).
_IONWAVE_LABELS = (
    r"(?:Bid\s+Number|Bid\s+Title|Title|Description|Open\s+Date|Issue\s+Date"
    r"|Clos(?:e|ing)\s+Date|Question\s+Cut\s*Off(?:\s+Date)?|Bid\s+Notes"
    r"|Bid\s+Contact)"
)
_IONWAVE_BIDNO_RE = re.compile(r"Bid\s+Number\s*:\s*", re.IGNORECASE)
_IONWAVE_TITLE_RE = re.compile(r"(?:Bid\s+)?Title\s*:", re.IGNORECASE)


def _ionwave_field(block: str, label: str) -> str:
    """Value after 'Label:' up to the next known IonWave label (or block end)."""
    m = re.search(
        rf"{label}\s*:\s*(.*?)\s*(?=(?:{_IONWAVE_LABELS})\s*:|$)",
        block, re.IGNORECASE | re.DOTALL,
    )
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def split_ionwave_digest(msg: dict) -> list[dict] | None:
    """Split an IonWave structured alert into one sub-message per bid.

    Returns a list of normalized sub-messages (subject = the real bid title,
    body = that bid's block, with the bid number carried as
    `solicitation_number`), or None when the message is not an IonWave-style
    structured digest — so the caller falls back to the generic single-message
    parse.
    """
    sender = (msg.get("sender") or "").lower()
    body = msg.get("body") or ""
    if "ionwave" not in sender:
        return None
    starts = [m.start() for m in _IONWAVE_BIDNO_RE.finditer(body)]
    if not starts or not _IONWAVE_TITLE_RE.search(body):
        return None

    bounds = starts + [len(body)]
    subs: list[dict] = []
    for i, start in enumerate(starts):
        block = body[start:bounds[i + 1]]
        title = _ionwave_field(block, r"(?:Bid\s+)?Title")
        if not title:
            continue
        bid_no = _ionwave_field(block, r"Bid\s+Number")
        subs.append({
            "id": f"{msg.get('id', '')}#{slugify(bid_no) or i + 1}",
            "sender": msg.get("sender") or "",
            "subject": title,
            "date": msg.get("date", ""),
            "body": block,
            "solicitation_number": bid_no,
        })
    return subs or None


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
        "next_action": "Triage: verify portal details, confirm specs, then decide bid/no-bid",
        "created_date": today,
        "last_reviewed": today,
        "notes": f"Auto-ingested from {source} email alert; verify details on the portal",
        "procurement_risk": "medium",
        "gate_status": "triage",
        "compliance_blocker": "portal_verification_pending; specs_pending",
    })
    # Honor a pre-extracted solicitation number (e.g. IonWave "Bid Number").
    soln = (msg.get("solicitation_number") or "").strip()
    if soln:
        row["solicitation_number"] = soln
    return row


# --------------------------------------------------------------------------
# Dedup + ingest (mirrors ingest_sam.py)
# --------------------------------------------------------------------------
def row_dedupe_keys(row: dict) -> set[str]:
    """Stable keys for recognizing the same opportunity across alert types."""
    keys = set()
    oid = (row.get("opportunity_id") or "").strip()
    if oid:
        keys.add(f"id:{oid}")
    source = (row.get("source") or "").strip().lower()
    soln = (row.get("solicitation_number") or "").strip().lower()
    if source and soln:
        keys.add(f"sol:{source}:{soln}")
    return keys


def existing_ids(rows: list[dict]) -> set[str]:
    keys: set[str] = set()
    for row in rows:
        keys.update(row_dedupe_keys(row))
    return keys


def ingest(messages: Iterable[dict], existing_rows: list[dict], today: str,
           home_states: frozenset[str] = relevance.HOME_STATES_DEFAULT,
           existing_leads: list[dict] | None = None,
           review_target: str = "leads"
           ) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    """Partition messages into (new_rows, leads, dupes, skipped, rejected).

    Each parsed row is gated by the central mattress-relevance classifier:
      REJECT -> rejected (never written anywhere but an optional audit log);
      REVIEW -> routed per `review_target` (default 'leads'): a broad upstream
                signal goes to Lead Radar (`leads`) instead of polluting the
                strict active bid pipeline. 'active' keeps the old behavior
                (kept as a HUMAN-flagged watching row); 'reject-log' drops it.
      ACCEPT -> kept as a normal watching row in the active pipeline (new_rows).
    leads: REVIEW rows mapped onto the Lead Radar schema.
    dupes: rows already tracked (active/archive for ACCEPT; Lead Radar +
           active/archive for leads).
    skipped: messages that produced no usable row (no title).
    """
    existing_leads = existing_leads or []
    ids = existing_ids(existing_rows)
    # Lead dedup spans existing Lead Radar rows AND active/archive rows, so a
    # broad signal already tracked (as a lead or a live bid) is not re-added.
    lead_ids: set[str] = set()
    for r in existing_leads:
        lead_ids |= lead_radar.lead_match_keys(r)
    for r in existing_rows:
        lead_ids |= lead_radar.lead_match_keys(r)

    seen: set[str] = set()
    lead_seen: set[str] = set()
    new_rows: list[dict] = []
    leads: list[dict] = []
    dupes: list[dict] = []
    skipped: list[dict] = []
    rejected: list[dict] = []
    # Recover original portal sender/subject from forwarded alerts first (so
    # source mapping + per-sender adapters work), then expand IonWave multi-bid
    # digests into one unit per bid; other messages pass through unchanged.
    units: list[dict] = []
    for msg in messages:
        msg = unwrap_forwarded(msg)
        units.extend(split_ionwave_digest(msg) or [msg])
    for msg in units:
        row = parse_message(msg, today)
        if row is None:
            skipped.append(msg)
            continue
        text = "\n".join(p for p in (row["title"], msg.get("body", ""),
                                     row.get("commodity_terms", "")) if p)
        verdict = relevance.classify(text, buyer=row.get("buyer", ""),
                                     source=row.get("source", ""),
                                     home_states=home_states)
        row["fit_score"] = str(verdict.confidence)
        row["notes"] = (f"{row.get('notes', '')}; relevance={verdict.decision}").strip("; ")
        if verdict.decision == "REJECT":
            row["next_action"] = "; ".join(verdict.reasons[:2])
            rejected.append(row)
            continue
        if verdict.decision == "REVIEW":
            if review_target == "reject-log":
                row["next_action"] = "HUMAN: confirm mattress scope — " + "; ".join(verdict.reasons[:2])
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
            # review_target == "active": fall through to the active pipeline,
            # flagged for human confirmation (legacy behavior).
            row["next_action"] = "HUMAN: confirm mattress scope — " + "; ".join(verdict.reasons[:2])
        keys = row_dedupe_keys(row)
        if keys & ids or keys & seen:
            dupes.append(row)
            continue
        seen.update(keys)
        new_rows.append(row)
    return new_rows, leads, dupes, skipped, rejected


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
    # Surface <a href="..."> targets so opportunity links survive tag
    # removal (HTML alerts put the URL in the attribute, not the text).
    text = re.sub(r'(?i)<a\b[^>]*?href=["\']([^"\']+)["\'][^>]*>', r" \1 ", text)
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


# --------------------------------------------------------------------------
# Microsoft Graph REST client (stdlib urllib; app-only client-credentials)
# --------------------------------------------------------------------------
def get_graph_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Client-credentials (app-only) token for Microsoft Graph."""
    url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }).encode("utf-8")
    payload = _http_json(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    token = payload.get("access_token")
    if not token:
        raise RuntimeError("Graph token endpoint returned no access_token")
    return token


def normalize_graph_message(msg: dict) -> dict:
    """Map a Graph message resource onto the tool's normalized message dict."""
    body = msg.get("body") or {}
    content = body.get("content") or msg.get("bodyPreview") or ""
    if (body.get("contentType") or "").lower() == "html":
        content = _strip_html(content)
    sender = (((msg.get("from") or {}).get("emailAddress")) or {}).get("address") or ""
    return {
        "id": msg.get("id") or "",
        "sender": sender,
        "subject": msg.get("subject") or "",
        "date": msg.get("receivedDateTime") or "",
        "body": content,
    }


def fetch_graph_messages(access_token: str, mailbox: str, *, folder: str | None,
                         since_iso: str, max_messages: int) -> list[dict]:
    """Fetch messages from an Outlook/M365 mailbox via Microsoft Graph."""
    base = f"{GRAPH_BASE}/users/{urllib.parse.quote(mailbox)}"
    path = f"/mailFolders/{urllib.parse.quote(folder)}/messages" if folder else "/messages"
    params = {
        "$filter": f"receivedDateTime ge {since_iso}",
        "$select": "id,subject,from,receivedDateTime,body,bodyPreview",
        "$orderby": "receivedDateTime desc",
        "$top": str(min(50, max_messages)),
    }
    url = base + path + "?" + urllib.parse.urlencode(params, safe="$ ,:")
    # Prefer plain-text bodies so we avoid lossy HTML stripping where possible.
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Prefer": 'outlook.body-content-type="text"',
    }
    out: list[dict] = []
    while url and len(out) < max_messages:
        payload = _http_json(url, headers=headers)
        for msg in payload.get("value") or []:
            out.append(normalize_graph_message(msg))
            if len(out) >= max_messages:
                break
        url = payload.get("@odata.nextLink")
    return out


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


def _require_env(names: list[str]) -> list[str]:
    vals = [os.environ.get(n) for n in names]
    missing = [n for n, v in zip(names, vals) if not v]
    if missing:
        raise SystemExit(
            f"error: missing env var(s): {', '.join(missing)}. Required for live "
            "ingest (or pass --fixture). See docs/email_ingest_setup.md. "
            "Never commit these secrets."
        )
    return vals  # type: ignore[return-value]


# --------------------------------------------------------------------------
# IMAP client (stdlib imaplib; app-password auth — no OAuth, no admin)
# --------------------------------------------------------------------------
def _imap_decode_header(value: str) -> str:
    """Decode RFC 2047 encoded-word headers (=?UTF-8?B?..?=) to plain text."""
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _imap_text_body(msg: "email.message.Message") -> str:
    """Best-effort body: prefer text/plain, fall back to stripped text/html.

    Skips attachments and honors each part's declared charset.
    """
    plain = ""
    html = ""
    parts = msg.walk() if msg.is_multipart() else [msg]
    for part in parts:
        if part.is_multipart():
            continue
        if "attachment" in (part.get("Content-Disposition") or "").lower():
            continue
        ctype = (part.get_content_type() or "").lower()
        if ctype not in ("text/plain", "text/html"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if ctype == "text/plain" and not plain:
            plain = text
        elif ctype == "text/html" and not html:
            html = text
    return plain or _strip_html(html)


def normalize_imap_message(raw: bytes) -> dict:
    """Map a raw RFC822 message onto the tool's normalized message dict.

    Same {id, sender, subject, date, body} shape as the Graph/Gmail providers,
    so the unwrap/split/relevance chain downstream is provider-agnostic.
    """
    msg = email.message_from_bytes(raw)
    return {
        "id": (msg.get("Message-ID") or "").strip(),
        "sender": _imap_decode_header(msg.get("From") or ""),
        "subject": _imap_decode_header(msg.get("Subject") or ""),
        "date": (msg.get("Date") or "").strip(),
        "body": _imap_text_body(msg),
    }


def fetch_imap_messages(address: str, app_password: str, *, since_date: str,
                        folder: str = "INBOX", max_messages: int = DEFAULT_MAX_MESSAGES,
                        host: str = "imap.gmail.com", port: int = 993) -> list[dict]:
    """Fetch recent messages over IMAP4 (TLS) using app-password auth.

    No admin and no OAuth: a self-issued app password + stdlib imaplib. Opens the
    mailbox READ-ONLY (never marks alerts seen) and returns the same normalized
    message dicts as the Graph/Gmail providers. `since_date` is IMAP
    'DD-Mon-YYYY' (e.g. '01-Jun-2026').
    """
    out: list[dict] = []
    imap = imaplib.IMAP4_SSL(host, port)
    try:
        imap.login(address, app_password)
        imap.select(folder, readonly=True)
        status, data = imap.search(None, "SINCE", since_date)
        if status != "OK":
            return out
        nums = (data[0] or b"").split()
        # Newest first, capped at max_messages.
        for num in reversed(nums[-max_messages:]):
            status, msg_data = imap.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data:
                continue
            raw = next((p[1] for p in msg_data if isinstance(p, tuple) and p[1]), None)
            if raw:
                out.append(normalize_imap_message(raw))
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return out


def _load_messages(args, today: str) -> list[dict]:
    if args.fixture:
        with open(args.fixture, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, list):
            raise ValueError("fixture must be a JSON list of message objects")
        return data

    if args.provider == "imap":
        address, app_password = _require_env(["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"])
        since_date = (datetime.fromisoformat(today) - timedelta(days=args.since_days)).strftime("%d-%b-%Y")
        return fetch_imap_messages(
            address, app_password, since_date=since_date,
            folder=args.imap_folder, max_messages=args.max_messages,
            host=args.imap_host,
        )

    if args.provider == "graph":
        tenant, client_id, client_secret, mailbox = _require_env(
            ["GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_MAILBOX"]
        )
        since_iso = (datetime.fromisoformat(today) - timedelta(days=args.since_days)).strftime(
            "%Y-%m-%dT00:00:00Z"
        )
        token = get_graph_token(tenant, client_id, client_secret)
        return fetch_graph_messages(
            token, mailbox, folder=args.graph_folder, since_iso=since_iso,
            max_messages=args.max_messages,
        )

    # provider == "gmail"
    client_id, client_secret, refresh_token = _require_env(
        ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]
    )
    access_token = get_access_token(client_id, client_secret, refresh_token)
    return fetch_messages(access_token, args.query, args.max_messages)


_HTTP_HINTS = {
    400: "bad request — check GRAPH_TENANT_ID / client id / secret (invalid_client?).",
    401: "token rejected — check GRAPH_CLIENT_SECRET (or GMAIL_REFRESH_TOKEN).",
    403: "access denied — grant the Mail.Read application permission and admin-consent it "
         "(and ensure the app-access policy allows this mailbox).",
    404: "not found — check GRAPH_MAILBOX (UPN) and the --graph-folder display name.",
}


def _print_http_hint(exc: urllib.error.HTTPError) -> None:
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")[:300]
    except Exception:
        pass
    print(f"  HTTP {exc.code}: {body}")
    if exc.code in _HTTP_HINTS:
        print(f"  hint: {_HTTP_HINTS[exc.code]}")


def _run_check(args, today: str) -> int:
    """Stepwise connectivity diagnostics for first-time credential setup."""
    print(f"Connectivity check - provider: {args.provider}")
    try:
        if args.provider == "imap":
            address, app_password = _require_env(["GMAIL_ADDRESS", "GMAIL_APP_PASSWORD"])
            since_date = (datetime.fromisoformat(today) - timedelta(days=args.since_days)).strftime("%d-%b-%Y")
            print(f"  mailbox: {address}  host: {args.imap_host}  folder: {args.imap_folder}  "
                  f"window: {args.since_days}d (SINCE {since_date})")
            print("  [1/3] connecting + login (app password) ...", end=" ")
            messages = fetch_imap_messages(
                address, app_password, since_date=since_date,
                folder=args.imap_folder, max_messages=args.max_messages,
                host=args.imap_host,
            )
            print("OK")
        elif args.provider == "graph":
            tenant, client_id, client_secret, mailbox = _require_env(
                ["GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_MAILBOX"]
            )
            print(f"  mailbox: {mailbox}  folder: {args.graph_folder or '(all mail)'}  "
                  f"window: {args.since_days}d")
            print("  [1/3] acquiring Microsoft Graph token ...", end=" ")
            token = get_graph_token(tenant, client_id, client_secret)
            print("OK")
            since_iso = (datetime.fromisoformat(today) - timedelta(days=args.since_days)).strftime(
                "%Y-%m-%dT00:00:00Z"
            )
            print("  [2/3] reading mailbox ...", end=" ")
            messages = fetch_graph_messages(
                token, mailbox, folder=args.graph_folder, since_iso=since_iso,
                max_messages=args.max_messages,
            )
            print("OK")
        else:
            client_id, client_secret, refresh_token = _require_env(
                ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"]
            )
            print(f"  query: {args.query!r}")
            print("  [1/3] acquiring Gmail token ...", end=" ")
            token = get_access_token(client_id, client_secret, refresh_token)
            print("OK")
            print("  [2/3] reading mailbox ...", end=" ")
            messages = fetch_messages(token, args.query, args.max_messages)
            print("OK")
    except urllib.error.HTTPError as exc:
        print("FAILED")
        _print_http_hint(exc)
        return 1
    except urllib.error.URLError as exc:
        print(f"FAILED\n  network error: {exc}")
        return 1
    except (imaplib.IMAP4.error, OSError) as exc:
        print(f"FAILED\n  IMAP error: {exc}\n  hint: check GMAIL_ADDRESS / GMAIL_APP_PASSWORD, "
              f"that IMAP is enabled (Gmail settings) and 2-Step Verification is on.")
        return 1
    except RuntimeError as exc:
        print(f"FAILED\n  {exc}")
        return 1

    new_rows, leads, _, skipped, rejected = ingest(messages, [], today)
    print(f"  [3/3] parsed {len(messages)} message(s); {len(new_rows)} active-relevant, "
          f"{len(leads)} lead(s), {len(rejected)} filtered out, {len(skipped)} no-title:")
    for r in new_rows[:5]:
        print(f"    + [{r['source']}] {r['title']}  due={r['due_date'] or '?'}  url={r['portal_url'] or '?'}")
    for lead in leads[:5]:
        print(f"    ~ [lead/{lead['lead_type']}] {lead['title']}  due={lead['due_date'] or '?'}")
    print("connectivity check OK (no rows written)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", choices=("graph", "gmail", "imap"), default="graph",
                        help="Mailbox backend: 'graph' (Outlook/M365, default), 'gmail' (REST/OAuth), "
                             "or 'imap' (Gmail app-password, no admin). Ignored when --fixture is given.")
    parser.add_argument("--since-days", type=int, default=DEFAULT_SINCE_DAYS,
                        help=f"[graph/imap] Look back this many days (default {DEFAULT_SINCE_DAYS}).")
    parser.add_argument("--graph-folder", default=None,
                        help="[graph] Restrict to a mail folder by display name (e.g. "
                             "'Procurement Alerts'). Default: search the whole mailbox.")
    parser.add_argument("--imap-folder", default="INBOX",
                        help="[imap] Mailbox/label to read; Gmail labels appear as folders "
                             "(e.g. 'Procurement/Alerts'). Default: INBOX.")
    parser.add_argument("--imap-host", default="imap.gmail.com",
                        help="[imap] IMAP host (default imap.gmail.com).")
    parser.add_argument("--query", default=DEFAULT_QUERY,
                        help=f"[gmail] Gmail search query for alert emails (default: {DEFAULT_QUERY!r})")
    parser.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES,
                        help=f"Safety cap on messages fetched (default {DEFAULT_MAX_MESSAGES}).")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE),
                        help=f"Pipeline CSV write target for ACCEPT rows (default: {DEFAULT_ACTIVE.relative_to(REPO_ROOT)})")
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE),
                        help=f"Archive CSV consulted for dedup only; never written. Default: {DEFAULT_ARCHIVE.relative_to(REPO_ROOT)}")
    parser.add_argument("--leads", default=str(lead_radar.DEFAULT_REVIEW),
                        help=f"Lead Radar CSV write target for REVIEW rows (default: {lead_radar.DEFAULT_REVIEW.relative_to(REPO_ROOT)})")
    parser.add_argument("--review-target", choices=("leads", "active", "reject-log"), default="leads",
                        help="Where REVIEW-band items go: 'leads' (Lead Radar, default), "
                             "'active' (legacy: active pipeline, HUMAN-flagged), or 'reject-log'.")
    parser.add_argument("--check", action="store_true",
                        help="Connectivity check: verify credentials + mailbox access with "
                             "stepwise diagnostics, print a parse preview, write nothing.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added; do not write.")
    parser.add_argument("--reject-log", default=None,
                        help="Optional CSV path to append relevance-rejected rows for audit/tuning.")
    parser.add_argument("--fixture", default=None,
                        help="Read a JSON list of normalized messages instead of calling Gmail (testing).")
    args = parser.parse_args(argv)

    today = datetime.now().date().isoformat()

    if args.check:
        return _run_check(args, today)

    active_path = Path(args.active)
    archive_path = Path(args.archive)
    leads_path = Path(args.leads)
    existing_active = _read_existing_or_empty(active_path)
    existing_archive = _read_existing_or_empty(archive_path)
    existing_rows = existing_active + existing_archive
    existing_leads = _read_existing_leads_or_empty(leads_path)

    messages = _load_messages(args, today)
    new_rows, leads, dupes, skipped, rejected = ingest(
        messages, existing_rows, today, existing_leads=existing_leads,
        review_target=args.review_target)

    print(f"email alerts fetched: {len(messages)} message(s)")
    print(f"  active:  {len(new_rows)}")
    print(f"  leads:   {len(leads)} (review -> {args.review_target})")
    print(f"  dupes:   {len(dupes)}")
    print(f"  rejected: {len(rejected)} (not mattress-relevant)")
    print(f"  skipped: {len(skipped)} (no usable title)")
    for r in new_rows:
        print(f"  + [{r['source']}] {r['opportunity_id']} :: {r['title']}")
    for lead in leads:
        print(f"  ~ [lead/{lead['lead_type']}] {lead['lead_id']} :: {lead['title']}")

    if args.reject_log and rejected:
        _append_reject_log(Path(args.reject_log), rejected)
        print(f"  logged {len(rejected)} rejected row(s) to {args.reject_log}")

    if args.dry_run:
        print("(--dry-run: no files written)")
        return 0

    wrote_anything = False
    if new_rows:
        write_rows_atomic(active_path, existing_active + new_rows)
        print(f"wrote {len(new_rows)} active row(s) to {active_path}")
        wrote_anything = True
    if leads:
        lead_radar.write_lead_rows_atomic(leads_path, existing_leads + leads)
        print(f"wrote {len(leads)} lead(s) to {leads_path}")
        wrote_anything = True
    if not wrote_anything:
        print("(no new rows to write)")
    return 0


def _append_reject_log(path: Path, rejected: list[dict]) -> None:
    """Append rejected rows to a CSV (created with header if absent)."""
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CANONICAL_HEADER, lineterminator="\n",
                                extrasaction="ignore")
        if not exists:
            writer.writeheader()
        for row in rejected:
            writer.writerow(row)


if __name__ == "__main__":
    raise SystemExit(main())
