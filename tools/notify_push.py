#!/usr/bin/env python3
"""
notify_push.py — email Blake when new mattress opportunities land.

The awareness layer's "push to the operator." After an ingest run adds rows,
this emails a short digest of what's new so Blake learns about a fit without
having to watch GitHub. It selects rows by `created_date` (new rows carry the
run date), formats a plain-text email, and sends it via Gmail SMTP reusing the
same app password the IMAP reader uses (no new credential).

Channels/secrets (env):
  GMAIL_ADDRESS       sender mailbox (also the SMTP login)
  GMAIL_APP_PASSWORD  the 16-char Gmail app password (same as --provider imap)
  NOTIFY_EMAIL_TO     fallback recipient when --to is not given (else GMAIL_ADDRESS)

Notification policy (2026-09-08): the operator gets ONE email per digest slot
(Mon/Thu) at the single business mailbox the workflow passes via --to
(DIGEST_EMAIL_TO secret). Ingest runs do not email; their new rows are folded
into the digest via --since-days/--print. No GitHub issue is used as a mail
channel any more (issue comments/assignments generated GitHub notification
mail to a second mailbox).

Design intent: NON-FATAL by default. A send error prints a warning and exits
0 so an ingest PR/commit still lands. The digest itself passes --strict so a
failed delivery fails the run (delivery IS the job there).

Usage:
    # real send (creds in env), notifying about rows created today
    python tools/notify_push.py --pr-url https://github.com/.../pull/123
    # preview without sending (CI / testing)
    python tools/notify_push.py --created-date 2026-06-27 --dry-run
    # generic mode: send an arbitrary subject + body file (e.g. the Mon/Thu digest)
    python tools/notify_push.py --subject "[Silverline] Procurement digest 2026-08-31" --body-file /tmp/digest.md --to ops@example.com --strict
    # digest section: print (no send) the rows created in the last 4 days
    python tools/notify_push.py --since-days 4 --print

Stdlib only (smtplib, email).
"""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import lead_radar  # noqa: E402
import demand_radar  # noqa: E402


def _in_window(value: str, end_date: str, since_days: int) -> bool:
    """True when ISO date `value` falls in [end_date - since_days, end_date].

    since_days=0 keeps the original exact-day behaviour. Dates are compared as
    ISO strings, so a malformed value never matches.
    """
    value = (value or "").strip()
    if not value:
        return False
    if since_days <= 0:
        return value == end_date
    try:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return value == end_date
    start = (end - timedelta(days=since_days)).isoformat()
    return start <= value <= end_date


def select_new_rows(active_rows: list[dict], lead_rows: list[dict], created_date: str,
                    since_days: int = 0) -> tuple[list[dict], list[dict]]:
    """Rows added on `created_date` (or within the trailing `since_days` window
    ending there) — the new ACCEPT bids and new Lead Radar leads."""
    accepts = [r for r in active_rows if _in_window(r.get("created_date"), created_date, since_days)]
    leads = [r for r in lead_rows if _in_window(r.get("created_date"), created_date, since_days)]
    return accepts, leads


def select_new_demand_rows(demand_rows: list[dict], created_date: str,
                           since_days: int = 0) -> list[dict]:
    """Demand Radar rows first seen on `created_date` (or in the trailing window).

    Mirrors `select_new_rows`' date logic, but pre-RFP demand signals carry their
    discovery date in `first_seen` (there is no bid `created_date`). Kept separate
    so the Demand Radar lane never mixes with the bid pipeline.
    """
    return [r for r in demand_rows if _in_window(r.get("first_seen"), created_date, since_days)]


def _demand_window_sort_key(r: dict) -> tuple:
    """Ascending by est_buy_window (YYYY-MM); blank/missing windows sort last."""
    bw = (r.get("est_buy_window") or "").strip()
    return (1, "") if not bw else (0, bw)


def _win_sort_key(r: dict) -> tuple:
    """Descending by win_score (blanks last); for sorting digest rows so the
    best opportunities lead the email."""
    raw = (r.get("win_score") or "").strip()
    try:
        return (0, -int(raw))
    except ValueError:
        return (1, 0)


def _fmt_row(r: dict, id_field: str) -> str:
    title = r.get("title") or "(no title)"
    source = r.get("source") or "?"
    due = r.get("due_date") or "?"
    url = r.get("portal_url") or ""
    fit = r.get("fit_score") or "?"
    win = (r.get("win_score") or "").strip()
    win_bit = f" | win: {win}" if win else ""
    line = f"  - {title}\n    source: {source} | due: {due} | fit: {fit}{win_bit}"
    if url:
        line += f"\n    {url}"
    return line


def _fmt_demand_row(r: dict) -> str:
    """One Demand Radar line: segment · scale · buy-window · location · facility · URL.

    Deliberately distinct from `_fmt_row` so a pre-RFP demand signal can never be
    read as a biddable solicitation.
    """
    segment = r.get("segment") or "?"
    scale = r.get("scale") or "?"
    window = r.get("est_buy_window") or "TBD"
    location = r.get("location") or "?"
    facility = r.get("facility_name") or r.get("demand_id") or "(unnamed)"
    url = r.get("source_url") or ""
    line = (f"  - {segment} · {scale} · buy-window {window} · {location} · {facility}")
    if url:
        line += f"\n    {url}"
    return line


def build_email(accepts: list[dict], leads: list[dict], pr_url: str, date: str,
                demand: list[dict] | None = None) -> tuple[str, str]:
    """Return (subject, body) for the digest. Caller decides whether to send."""
    demand = demand or []
    n_a, n_l, n_d = len(accepts), len(leads), len(demand)
    bits = []
    if n_a:
        bits.append(f"{n_a} bid fit{'s' if n_a != 1 else ''}")
    if n_l:
        bits.append(f"{n_l} lead{'s' if n_l != 1 else ''}")
    if n_d:
        bits.append(f"{n_d} demand")
    summary = " + ".join(bits) if bits else "no new rows"
    subject = f"[Silverline] {summary} - {date}"

    lines = [f"New procurement signals from the {date} ingest run.", ""]
    if accepts:
        lines.append("== ACTIVE BID FITS (review + decide bid/no-bid; ranked by win_score) ==")
        lines += [_fmt_row(r, "opportunity_id") for r in sorted(accepts, key=_win_sort_key)]
        lines.append("")
    if leads:
        lines.append("== LEAD RADAR (broad/ambiguous - confirm product fit before bidding) ==")
        lines += [_fmt_row(r, "lead_id") for r in sorted(leads, key=_win_sort_key)]
        lines.append("")
    if demand:
        lines.append("== DEMAND RADAR (pre-RFP construction signals — sales outreach, "
                     "sorted by buy-window) ==")
        lines += [_fmt_demand_row(r)
                  for r in sorted(demand, key=_demand_window_sort_key)]
        lines.append("")
    if pr_url:
        lines.append(f"Triage PR: {pr_url}")
    lines.append("")
    lines.append("(Automated alert from the Silverline procurement pipeline. "
                 "Verify every item on the portal before bidding.)")
    return subject, "\n".join(lines)


def build_failure_email(date: str, run_url: str,
                        workflow: str = "daily email-alert ingest") -> tuple[str, str]:
    """Return (subject, body) for a pipeline-failure alert."""
    subject = f"[Silverline] PIPELINE FAILED - {workflow} - {date}"
    body = (
        f"The {workflow} FAILED on {date}.\n\n"
        "This means a sweep or report did not complete, so new mattress/bedding "
        "opportunities in this window may have been missed.\n\n"
        + (f"Failed run: {run_url}\n\n" if run_url else "")
        + "What to do: open the run above, read the first red step (common causes: "
        "a bad GMAIL_APP_PASSWORD, the Procurement/Alerts label missing, or a code "
        "error), fix it, then re-run.\n"
    )
    return subject, body


def build_watchdog_email(window: int, run_url: str) -> tuple[str, str]:
    """Return (subject, body) for a zero-message (silent-pipe) alert."""
    subject = f"[Silverline] WATCHDOG - {window} runs with ZERO alerts (pipe may be broken)"
    body = (
        f"The last {window} daily email-ingest runs all fetched ZERO messages from the "
        "Procurement/Alerts label.\n\n"
        "Portals normally send some mail even in a quiet mattress market, so a sustained "
        "zero usually means the pipe is broken - the Power Automate flow stopped, the Gmail "
        "filter/label was renamed, or a portal dropped your notification contact.\n\n"
        + (f"Watchdog run: {run_url}\n\n" if run_url else "")
        + "What to do: (1) send yourself a test email with subject [PROC-ALERT] and confirm it "
        "lands under the Procurement/Alerts label; (2) check the 'Procurement alerts to Gmail' "
        "flow is still On at make.powerautomate.com.\n"
    )
    return subject, body


def send_email(*, host: str, port: int, address: str, app_password: str,
               to_addr: str, subject: str, body: str) -> None:
    """Send a plain-text email over SMTP-SSL. Raises on failure."""
    msg = EmailMessage()
    msg["From"] = address
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL(host, port, timeout=30) as smtp:
        smtp.login(address, app_password)
        smtp.send_message(msg)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--active", default=str(pipeline.DEFAULT_ACTIVE),
                        help="Active pipeline CSV (default: %(default)s)")
    parser.add_argument("--leads", default=str(lead_radar.DEFAULT_REVIEW),
                        help="Lead Radar CSV (default: %(default)s)")
    parser.add_argument("--demand", default=str(demand_radar.DEFAULT_REVIEW),
                        help="Demand Radar CSV (default: %(default)s)")
    parser.add_argument("--created-date", default=None,
                        help="Notify about rows created on this date (default: today, UTC-naive).")
    parser.add_argument("--since-days", type=int, default=0,
                        help="Widen the row selection to the trailing N days ending at --created-date "
                             "(the Mon/Thu digest uses 4 so nothing lands between slots unseen).")
    parser.add_argument("--print", dest="print_only", action="store_true",
                        help="Print the built body only (no headers, no send) - for embedding "
                             "in the digest. Prints a one-line note when nothing is new.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on missing creds/recipient or a send error (default: warn, exit 0).")
    parser.add_argument("--workflow", default="daily email-alert ingest",
                        help="Workflow name to cite in a --failure alert.")
    parser.add_argument("--pr-url", default="", help="Triage PR URL to include in the email.")
    parser.add_argument("--failure", action="store_true",
                        help="Send a 'pipeline failed' alert instead of a digest (for the workflow's if:failure step).")
    parser.add_argument("--run-url", default="", help="Failed/watchdog run URL to include in the alert.")
    parser.add_argument("--watchdog", action="store_true",
                        help="Send a 'zero alerts / silent pipe' alert (for the watchdog workflow).")
    parser.add_argument("--window", type=int, default=0,
                        help="Number of consecutive zero-fetch runs, for a --watchdog alert.")
    parser.add_argument("--to", default=None,
                        help="Recipient (default: NOTIFY_EMAIL_TO env, else GMAIL_ADDRESS).")
    parser.add_argument("--subject", default=None,
                        help="Generic mode: subject for an arbitrary email (requires --body-file).")
    parser.add_argument("--body-file", default=None,
                        help="Generic mode: text/markdown file to send as the body (requires --subject).")
    parser.add_argument("--smtp-host", default="smtp.gmail.com")
    parser.add_argument("--smtp-port", type=int, default=465)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the email instead of sending (no creds needed).")
    args = parser.parse_args(argv)

    created_date = args.created_date or datetime.now().date().isoformat()

    if args.subject or args.body_file:
        # Generic mode: ship an already-built document (e.g. the Mon/Thu
        # digest the workflow wrote to /tmp/digest.md). Flag misuse is a
        # developer error and exits 2; a missing body file at runtime is
        # non-fatal by design (warn + exit 0, like every other send problem).
        if not (args.subject and args.body_file):
            print("error: --subject and --body-file must be used together.", file=sys.stderr)
            return 2
        body_path = Path(args.body_file)
        if not body_path.exists():
            print(f"notify: WARNING - body file not found: {body_path}; skipping email "
                  "(this did not fail the run).", file=sys.stderr)
            return 0
        subject, body = args.subject, body_path.read_text(encoding="utf-8")
    elif args.watchdog:
        subject, body = build_watchdog_email(args.window, args.run_url)
    elif args.failure:
        subject, body = build_failure_email(created_date, args.run_url, args.workflow)
    else:
        active_rows = pipeline.read_rows(Path(args.active))[1] if Path(args.active).exists() else []
        lead_rows = lead_radar.read_lead_rows(Path(args.leads))[1] if Path(args.leads).exists() else []
        demand_rows = demand_radar.read_demand_rows(Path(args.demand))[1] if Path(args.demand).exists() else []
        accepts, leads = select_new_rows(active_rows, lead_rows, created_date, args.since_days)
        demand = select_new_demand_rows(demand_rows, created_date, args.since_days)
        if not accepts and not leads and not demand:
            if args.print_only:
                span = (f"the {args.since_days} days ending {created_date}"
                        if args.since_days else created_date)
                print(f"No new active-bid, Lead Radar, or Demand Radar rows in {span}.")
            else:
                print(f"notify: nothing new for {created_date}; no email sent.")
            return 0
        subject, body = build_email(accepts, leads, args.pr_url, created_date, demand)

    if args.print_only:
        print(body)
        return 0

    if args.dry_run:
        print(f"--- DRY RUN (no email sent) ---\nTo: <recipient>\nSubject: {subject}\n\n{body}")
        return 0

    return _deliver(args, subject, body)


def _deliver(args, subject: str, body: str) -> int:
    """Send via Gmail SMTP. Non-fatal by default (warn + return 0 so a notify
    problem never fails an ingest job); with --strict a missing secret or a
    send error returns 1, because for the digest delivery IS the job."""
    strict = bool(getattr(args, "strict", False))
    level = "ERROR" if strict else "WARNING"
    address = os.environ.get("GMAIL_ADDRESS", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_addr = args.to or os.environ.get("NOTIFY_EMAIL_TO") or address
    if not address or not app_password or not to_addr:
        tail = "cannot deliver." if strict else "skipping email (this did not fail the run)."
        print(f"notify: {level} - GMAIL_ADDRESS / GMAIL_APP_PASSWORD / recipient not set; {tail}",
              file=sys.stderr)
        return 1 if strict else 0
    try:
        send_email(host=args.smtp_host, port=args.smtp_port, address=address,
                   app_password=app_password, to_addr=to_addr, subject=subject, body=body)
        print(f"notify: emailed {to_addr} - {subject}")
    except Exception as exc:  # noqa: BLE001 - non-fatal by design (unless --strict)
        tail = "" if strict else (" The run still succeeded; the digest's pipe-health "
                                  "section will show a sustained outage.")
        print(f"notify: {level} - email send failed ({exc!r}).{tail}", file=sys.stderr)
        return 1 if strict else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
