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
  NOTIFY_EMAIL_TO     where to email Blake (default: GMAIL_ADDRESS, i.e. yourself)

Design intent: NON-FATAL. A send error must never fail the ingest job — it
prints a warning and exits 0 so the PR/commit still lands. Reliability is
covered separately by the if:failure() alert and the zero-message watchdog.

Usage:
    # real send (creds in env), notifying about rows created today
    python tools/notify_push.py --pr-url https://github.com/.../pull/123
    # preview without sending (CI / testing)
    python tools/notify_push.py --created-date 2026-06-27 --dry-run

Stdlib only (smtplib, email).
"""

from __future__ import annotations

import argparse
import os
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import lead_radar  # noqa: E402


def select_new_rows(active_rows: list[dict], lead_rows: list[dict], created_date: str
                    ) -> tuple[list[dict], list[dict]]:
    """Rows added on `created_date` — the new ACCEPT bids and new Lead Radar leads."""
    accepts = [r for r in active_rows if (r.get("created_date") or "") == created_date]
    leads = [r for r in lead_rows if (r.get("created_date") or "") == created_date]
    return accepts, leads


def _fmt_row(r: dict, id_field: str) -> str:
    title = r.get("title") or "(no title)"
    source = r.get("source") or "?"
    due = r.get("due_date") or "?"
    url = r.get("portal_url") or ""
    fit = r.get("fit_score") or "?"
    line = f"  - {title}\n    source: {source} | due: {due} | fit: {fit}"
    if url:
        line += f"\n    {url}"
    return line


def build_email(accepts: list[dict], leads: list[dict], pr_url: str, date: str
                ) -> tuple[str, str]:
    """Return (subject, body) for the digest. Caller decides whether to send."""
    n_a, n_l = len(accepts), len(leads)
    bits = []
    if n_a:
        bits.append(f"{n_a} bid fit{'s' if n_a != 1 else ''}")
    if n_l:
        bits.append(f"{n_l} lead{'s' if n_l != 1 else ''}")
    summary = " + ".join(bits) if bits else "no new rows"
    subject = f"[Silverline] {summary} - {date}"

    lines = [f"New procurement signals from the {date} ingest run.", ""]
    if accepts:
        lines.append("== ACTIVE BID FITS (review + decide bid/no-bid) ==")
        lines += [_fmt_row(r, "opportunity_id") for r in accepts]
        lines.append("")
    if leads:
        lines.append("== LEAD RADAR (broad/ambiguous - confirm product fit before bidding) ==")
        lines += [_fmt_row(r, "lead_id") for r in leads]
        lines.append("")
    if pr_url:
        lines.append(f"Triage PR: {pr_url}")
    lines.append("")
    lines.append("(Automated alert from the Silverline procurement pipeline. "
                 "Verify every item on the portal before bidding.)")
    return subject, "\n".join(lines)


def build_failure_email(date: str, run_url: str) -> tuple[str, str]:
    """Return (subject, body) for a pipeline-failure alert."""
    subject = f"[Silverline] PIPELINE FAILED - {date}"
    body = (
        f"The daily email-alert ingest FAILED on {date}.\n\n"
        "This means a sweep did not complete, so new mattress/bedding "
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
    parser.add_argument("--created-date", default=None,
                        help="Notify about rows created on this date (default: today, UTC-naive).")
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
    parser.add_argument("--smtp-host", default="smtp.gmail.com")
    parser.add_argument("--smtp-port", type=int, default=465)
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the email instead of sending (no creds needed).")
    args = parser.parse_args(argv)

    created_date = args.created_date or datetime.now().date().isoformat()

    if args.watchdog:
        subject, body = build_watchdog_email(args.window, args.run_url)
    elif args.failure:
        subject, body = build_failure_email(created_date, args.run_url)
    else:
        active_rows = pipeline.read_rows(Path(args.active))[1] if Path(args.active).exists() else []
        lead_rows = lead_radar.read_lead_rows(Path(args.leads))[1] if Path(args.leads).exists() else []
        accepts, leads = select_new_rows(active_rows, lead_rows, created_date)
        if not accepts and not leads:
            print(f"notify: nothing new for {created_date}; no email sent.")
            return 0
        subject, body = build_email(accepts, leads, args.pr_url, created_date)

    if args.dry_run:
        print(f"--- DRY RUN (no email sent) ---\nTo: <recipient>\nSubject: {subject}\n\n{body}")
        return 0

    return _deliver(args, subject, body)


def _deliver(args, subject: str, body: str) -> int:
    """Send via Gmail SMTP, non-fatally. A missing secret or send error warns
    and returns 0 so a notify problem never fails the ingest job."""
    address = os.environ.get("GMAIL_ADDRESS", "")
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_addr = args.to or os.environ.get("NOTIFY_EMAIL_TO") or address
    if not address or not app_password or not to_addr:
        print("notify: WARNING - GMAIL_ADDRESS / GMAIL_APP_PASSWORD / recipient not set; "
              "skipping email (this did not fail the run).", file=sys.stderr)
        return 0
    try:
        send_email(host=args.smtp_host, port=args.smtp_port, address=address,
                   app_password=app_password, to_addr=to_addr, subject=subject, body=body)
        print(f"notify: emailed {to_addr} - {subject}")
    except Exception as exc:  # noqa: BLE001 - non-fatal by design
        print(f"notify: WARNING - email send failed ({exc!r}); the ingest run still "
              "succeeded. The zero-message watchdog will catch a sustained outage.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
