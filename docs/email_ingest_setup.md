# Email-alert ingest — operator setup

The state/local and cooperative procurement portals do **not** publish
RSS feeds or documented opportunity APIs (verified June 2026: Bonfire,
IonWave, DemandStar, BidNet Direct, BuyBoard, Texas ESBD/SmartBuy, and
the TIPS/Choice Partners/HGACBuy/Sourcewell/OMNIA cooperatives are all
email-alert-or-login only). The one compliant, broadly-available channel
is the **commodity/NIGP-code email alert** each portal sends to a
registered supplier. `tools/ingest_email.py` reads those alerts from the
alert mailbox (stdlib `urllib`, no scraping, no browser automation) and
turns them into pipeline rows.

This replaces the *manual* weekly portal walk for the email-notification
sources. Submission stays manual; the tool only adds `watching` rows to
triage.

## Recommended path — route alerts to Gmail (no Azure admin)

The simplest, no-admin setup, and the current plan:

1. **Subscribe to the portal alerts** (section A) using
   **`blake.e.ford@gmail.com`** as the notification/contact address, so
   alerts land directly in a Gmail that an operator/assistant can read.
2. **Ingest, two flavors:**
   - **On-demand sweep (zero config):** an assistant with Gmail access
     reads the new alerts, runs them through the same tested parser
     (`ingest_email.py`), and opens a triage PR. Nothing to provision.
   - **Unattended (light, self-service):** mint a personal
     `gmail.readonly` OAuth refresh token (Google Cloud Console, your own
     Google account — no IT/admin), set `GMAIL_CLIENT_ID` /
     `GMAIL_CLIENT_SECRET` / `GMAIL_REFRESH_TOKEN` repo secrets, and run
     `ingest_email.py --provider gmail`.

The Outlook / Microsoft Graph backend below is an **alternative** for
running directly against the Outlook mailbox — it needs a tenant-admin
**Mail.Read** consent, so use it only if/when that's available.

---

## A. Subscribe to portal alerts and route them to one place

For each portal, register as a supplier (free unless noted), use
**`blake.e.ford@gmail.com`** as the notification address, select the
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

**Routing (Gmail, recommended):** use `blake.e.ford@gmail.com` as the
notification address on every portal — no rule needed; sweeps find alerts
by sender domain. **Routing (Outlook alternative):** if alerts go to the
Outlook mailbox instead, create an **Outlook rule** that files them into a
folder named **`Procurement Alerts`** (match sender domains `gobonfire.com`,
`ionwave.net`, `demandstar.com`, `bidnetdirect.com`, `buyboard.com`,
`txsmartbuy.gov`, etc.), which the Graph backend reads:

```
python tools/ingest_email.py --graph-folder "Procurement Alerts" --since-days 8
```

> Omit `--graph-folder` to scan the whole mailbox instead.

---

## B. Alternative: native Outlook via Microsoft Graph (requires tenant admin)

Use this only if you want the scheduled run to read the Outlook mailbox
directly. It authenticates as an **application** (client-credentials flow)
and needs a tenant-admin **Mail.Read** consent — which is why the
Gmail-routed path above is the default. The client secret *is* the
credential; no interactive login at run time.

1. In the **Entra admin center / Azure portal → App registrations**, create
   a new registration (single tenant). Note the **Application (client) ID**
   and **Directory (tenant) ID**.
2. **Certificates & secrets →** create a **client secret**. Copy its value
   now (shown once).
3. **API permissions → Add → Microsoft Graph → Application permissions →**
   add **`Mail.Read`**, then **Grant admin consent**.
4. *(Recommended, least-privilege)* restrict the app to only the alert
   mailbox with an **application access policy** (Exchange Online
   PowerShell `New-ApplicationAccessPolicy`), so the app can read only
   `beford@silverlinesleep.com`, not the whole tenant.

### Store as repo secrets

*Settings → Secrets and variables → Actions →* add:

- `GRAPH_TENANT_ID`  (Directory/tenant ID)
- `GRAPH_CLIENT_ID`  (Application/client ID)
- `GRAPH_CLIENT_SECRET`  (the secret value from step 2)
- `GRAPH_MAILBOX`  (`beford@silverlinesleep.com`)

**Never commit these.** The scheduled workflow fails fast with a clear
error if any are missing.

> *Gmail alternative:* if alerts are ever routed to a Gmail mailbox
> instead, set `GMAIL_CLIENT_ID` / `GMAIL_CLIENT_SECRET` /
> `GMAIL_REFRESH_TOKEN` (a `gmail.readonly` OAuth refresh token from
> Google Cloud Console) and run with `--provider gmail`.

---

## Running it

```sh
# Offline / test (no creds, no network): parse a fixture
python tools/ingest_email.py --fixture tests/fixtures/email_alerts_sample.json --dry-run

# Verify the Azure app + secrets work (stepwise diagnostics, writes nothing)
GRAPH_TENANT_ID=... GRAPH_CLIENT_ID=... GRAPH_CLIENT_SECRET=... GRAPH_MAILBOX=beford@silverlinesleep.com \
  python tools/ingest_email.py --check --graph-folder "Procurement Alerts" --since-days 8

# Live Outlook/M365: preview, then write
GRAPH_TENANT_ID=... GRAPH_CLIENT_ID=... GRAPH_CLIENT_SECRET=... GRAPH_MAILBOX=beford@silverlinesleep.com \
  python tools/ingest_email.py --graph-folder "Procurement Alerts" --since-days 8 --dry-run
```

Run `--check` first: it acquires a token, reads the mailbox folder, and
prints a parse preview, with actionable hints on the common 401/403/404
failures (bad secret, missing admin consent, wrong mailbox/folder).

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
