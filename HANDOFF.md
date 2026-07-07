# Resume prompt — Silverline-Sleep-Procurement

Copy the block below into a new Claude Code session to pick up work. Keep it
current as the project evolves. (Sessions with persistent memory get most of
this automatically — MEMORY.md is the authoritative "start here"; this file is
the fallback for memory-less sessions and human onboarding.)

```text
You are resuming work on the Silverline-Sleep-Procurement repository — a static,
stdlib-Python procurement toolkit that surfaces contract MATTRESS opportunities
(federal/state/local/private) into one human-reviewed pipeline. Vendor: Continental
Silverline Products, LLC (Houston TX; brands Restonic/Spring Air/Silverline Sleep;
institutional/dormitory/correctional/medical/fire-retardant mattresses; service
geography TX/OK/LA/MS/AR/NM). Final bid submission is always manual/human.

Trunk: main (work on claude/* branches, PR to merge; auto-ingest uses auto/*).

## Hard constraints
- Standard-library Python only (third-party needs approval).
- No portal scraping / no browser automation for data collection. Public APIs,
  RSS, or email only. (Operator-assisted browser sessions for REGISTRATIONS are OK.)
- No automatic bid submission. No committed secrets/credentials/private contacts/
  machine paths. Legal entity is the LLC — never "L.P." (dissolved 2015 predecessor).
- All outbound business email goes from silverlinesleep.com — keep outreach as
  markdown drafts in docs/drafts/; never stage/send via Gmail.
- Audit gate before every commit:
    python -m unittest discover -s tests        (475 pass as of 2026-07-07)
    python -m compileall -q tools tests
    python -m json.tool on every committed JSON
    python tools/validate_vendor_profile.py vendor-profiles/continental_silverline.profile.json
    python tools/workflow_check.py
    machine-path / personal-name / PII leak grep over committed files
      (exact regex lives in .github/workflows/ci.yml — do not paste it into a
      committed .md file or it self-matches the grep)

## Architecture (two lanes + one gate)
Every channel feeds raw items into ONE central mattress-relevance filter
(tools/relevance.py): ACCEPT -> bids/active/_pipeline.csv, REVIEW -> Lead Radar
(leads/review/_lead_radar.csv), REJECT -> logs/rejects/. Channels are pluggable
adapters. Lane 1 = public procurement (SAM API twice-weekly, RSS/Bonfire
twice-weekly, email alerts daily via Gmail IMAP). Lane 2 = private Demand Radar
(Google Alerts RSS, kind:"demand" in configs/feeds.json) — pre-RFP construction/
renovation signals for sales outreach, NOT biddable solicitations; triage is
manual in next_action/notes. Reliability: per-run failure emails, zero-message
watchdog, healthchecks.io dead-man's-switch, Monday digest on issue #43.
Re-bid prep windows: lead_radar.py calendar -> Google Calendar via MCP, state
ledger leads/review/_calendar_state.json.

## Where state lives (read these, not stale docs)
- python tools/dashboard.py            — live pipeline + deadlines
- docs/active_registrations.md         — registration/vendor-number ledger
- leads/review/_lead_radar.csv         — watch/research signals
- docs/demand_radar_next_steps.md      — Demand Radar plan (data-gated; don't
  build cockpit/enrichment before 20-50 real rows exist)
- GitHub issue #43 (digest) + open automation PRs

## Status snapshot (2026-07-07 — verify against the sources above)
- SAM.gov: registration SUBMITTED under the corrected LLC name (UEI XF73FG8CVMX1).
  Awaiting IRS TIN match -> DLA CAGE -> Active (ETA ~07-09..07-21). POC must
  answer any dla.mil email promptly. Do NOT cite the UEI until Active. When
  Active: record CAGE in the ledger, unblock pipeline rows, resume Choice
  Partners/HCDE registration.
- Pipeline: 2 active rows (JBSA dorm mattresses — Sources Sought answered,
  watching for RFQ; Army 411th CSB W51LL526QA005 — due 2026-07-10, likely
  no-bid since SAM won't be Active in time).
- First WIN: City of Austin Fire/EMS IFB 8300 DCG1033 (confirmed 2026-07-02),
  awaiting PO/delivery — outreach postponed by operator. Houston HFD bid
  submitted, award unknown — postponed. LaPAC statewide lost to Grand Bedding;
  re-bid watch 2027 (prep window on calendar).
- Email pipe: fixed 07-05/06 (Gmail filter OR-expression + Outlook rule repaired);
  issue #108 open ~1 week watching organic volume — if still silent, portal
  alert subscriptions are the next suspect.

Start by: git log --oneline -10; gh pr list; python tools/dashboard.py;
then read MEMORY.md / docs/active_registrations.md before acting.
```
