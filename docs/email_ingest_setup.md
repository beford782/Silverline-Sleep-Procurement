# Email-alert ingest — operator setup

The state/local and cooperative procurement portals do **not** publish
RSS feeds or documented opportunity APIs (verified June 2026: Bonfire,
IonWave, DemandStar, BidNet Direct, BuyBoard, Texas ESBD/SmartBuy, and
the TIPS/Choice Partners/HGACBuy/Sourcewell/OMNIA cooperatives are all
email-alert-or-login only). The one compliant, broadly-available channel
is the **commodity/NIGP-code email alert** each portal sends to a
registered supplier. `tools/ingest_email.py` reads those alerts from a
Gmail mailbox via the documented Gmail REST API (stdlib `urllib`, no
scraping, no browser automation) and turns them into pipeline rows.

This replaces the *manual* weekly portal walk for the email-notification
sources. Submission stays manual; the tool only adds `watching` rows to
triage.

There are two one-time setup tasks: **(A) subscribe to the alerts** and
route them to one Gmail label, and **(B) provision a Gmail OAuth token**
for the scheduled run. Neither can be automated for you — they require
portal logins and a Google consent screen.

---

## A. Subscribe to portal alerts and route them to one label

For each portal, register as a supplier (free unless noted), select the
mattress/bedding/institutional-furniture commodity codes, and turn on
email notifications. Suggested commodity vocabulary (already tracked in
the vendor's `portal-checklists/`): NIGP class **205** (bedding,
mattresses), plus institutional/dormitory/correctional/medical furniture
classes; NAICS **337910**.

| Portal | Where to register | Notes |
| --- | --- | --- |
| Bonfire (Harris County, universities) | each agency's `*.bonfirehub.com` vendor portal | free; pick commodity codes |
| IonWave (Houston ISD, TIPS, Choice Partners, OMNIA/Region 4 ESC) | each agency's `*.ionwave.net` supplier registration | free; NIGP-code bid invitations |
| DemandStar | demandstar.com | free tier = 1 agency; paid for broader coverage |
| BidNet Direct | bidnetdirect.com | free = limited region; paid for full matching |
| BuyBoard | buyboard.com vendor registration | emailed proposal invitations |
| Texas ESBD / CMBL | comptroller.texas.gov CMBL (fee) | NIGP-code notices |
| State boards (OMES, LaPAC, MAGIC, ARBuy, NM SPD) | each state supplier portal | email alerts where offered |

**Routing:** Have every alert land in the **alert inbox**
(`beford@silverlinesleep.com`) and create a Gmail **filter → label**
named `Procurement/Alerts` that catches them (match the portal sender
domains: `gobonfire.com`, `ionwave.net`, `demandstar.com`,
`bidnetdirect.com`, `buyboard.com`, `txsmartbuy.gov`, etc.). The ingest
default query is:

```
label:Procurement/Alerts newer_than:8d -in:trash -in:spam
```

> If you prefer to keep subscriptions on a different address, forward
> them into the labeled inbox, or change `--query` / `DEFAULT_QUERY`.

---

## B. Provision a Gmail OAuth refresh token (read-only)

The scheduled run authenticates as the alert mailbox using an OAuth2
**refresh token**. This is independent of any "connected account" — the
token *is* the credential.

1. In Google Cloud Console, create (or reuse) a project and **enable the
   Gmail API**.
2. Configure the OAuth consent screen; add the alert mailbox account as a
   test user (or publish). Scope needed: `gmail.readonly`.
3. Create an **OAuth client ID** of type *Desktop app*. Note the
   **client ID** and **client secret**.
4. Do the one-time consent to mint a **refresh token** for the alert
   mailbox with the `gmail.readonly` scope (e.g. via the OAuth 2.0
   Playground using your own client ID/secret, or a small local script).
   Keep the refresh token secret.

### Store as repo secrets

*Settings → Secrets and variables → Actions →* add:

- `GMAIL_CLIENT_ID`
- `GMAIL_CLIENT_SECRET`
- `GMAIL_REFRESH_TOKEN`

**Never commit these.** The scheduled workflow fails fast with a clear
error if any are missing.

---

## Running it

```sh
# Offline / test (no creds, no network): parse a fixture
python tools/ingest_email.py --fixture tests/fixtures/email_alerts_sample.json --dry-run

# Live (creds in env): preview, then write
GMAIL_CLIENT_ID=... GMAIL_CLIENT_SECRET=... GMAIL_REFRESH_TOKEN=... \
  python tools/ingest_email.py --query 'label:Procurement/Alerts newer_than:8d' --dry-run
```

Scheduled automatically by
`.github/workflows/weekly_email_ingest.yml` (Mondays 13:30 UTC + manual
`workflow_dispatch`): it ingests, re-scores, runs the repo checks, and —
if `bids/active/_pipeline.csv` changed — opens a PR for human triage. It
never auto-archives, auto-submits, or pushes to `main`.

---

## Parsing accuracy (important)

Alert-email layouts are vendor-specific and change over time. The bundled
parser is a deliberately **generic** extractor: it pulls the solicitation
**title** (from the subject, with notification prefixes stripped), the
**portal link**, and a **due date** (when present), and labels the
**source** from the sender domain. It never invents fields it cannot
find, so `buyer`, `delivery_location`, and `solicitation_number` may be
blank.

**Always verify each ingested row against the portal before acting.** As
real alert samples are captured, add per-sender adapters in
`SENDER_SOURCES` / `parse_message` (with fixtures in
`tests/fixtures/email_alerts_sample.json`) to extract richer fields.
