#!/usr/bin/env python3
"""
email_watchdog.py — decide whether the email-alert pipe has gone silent.

The daily IMAP ingest (daily_email_ingest.yml) can keep running green while
quietly fetching NOTHING — if the Power Automate flow stops, the Gmail
filter/label is renamed, or a portal drops the notification contact. That looks
identical to a quiet week unless you look across runs.

Key signal: the *fetched* count (messages pulled from the Procurement/Alerts
label), NOT the mattress-fit count. Portals send plenty of non-mattress alerts
too, so a working pipe normally fetches *some* mail even when no mattress bid is
live. A run of consecutive ZERO-fetch days is therefore a broken-pipe signal,
not just a quiet market.

This module is pure: it takes the recent fetched counts (gathered by the
workflow from prior run logs) and decides whether to alert. Stateless — no
committed counter, no false alarms before there's enough history.

Usage (from the watchdog workflow):
    python tools/email_watchdog.py --counts "0 0 0 0 0 0 0" --threshold 7
    -> prints a parseable `alert=true|false` line.

Stdlib only.
"""

from __future__ import annotations

import argparse
import sys


def should_alert(counts: list[int], threshold: int) -> bool:
    """True when there are >= `threshold` runs and EVERY one fetched zero.

    Requiring at least `threshold` data points avoids alarming a brand-new
    system that simply hasn't accumulated enough history yet.
    """
    counts = list(counts)
    return len(counts) >= threshold and all(int(c) == 0 for c in counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--counts", default="",
        help="Space-separated fetched-message counts from recent successful runs.")
    parser.add_argument(
        "--threshold", type=int, default=7,
        help="Alert only if at least this many runs are present AND all fetched 0 (default 7).")
    args = parser.parse_args(argv)

    raw = args.counts.split()
    try:
        counts = [int(x) for x in raw]
    except ValueError:
        print(f"counts=invalid ({args.counts!r})", file=sys.stderr)
        counts = []

    alert = should_alert(counts, args.threshold)
    # Human detail to stderr; clean key=value lines to stdout so a workflow can
    # append them straight to $GITHUB_OUTPUT.
    print(f"counts={counts} threshold={args.threshold}", file=sys.stderr)
    print(f"window={len(counts)}")
    print(f"threshold={args.threshold}")
    print(f"alert={'true' if alert else 'false'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
