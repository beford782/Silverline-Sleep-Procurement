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

## LIVE PATH (recommended, 2026-06-27): Gmail App-Password IMAP

This is the current operating design — "Silverline Awareness Bridge" (see
[`awareness_system_design.md`](awareness_system_design.md)). It needs **no Azure
admin and no OAuth token** that can expire: the daily workflow
`.github/workflows/daily_email_ingest.yml` reads a Gmail mailbox over IMAP with a
self-issued **app password**, relevance-gates each alert, opens a triage PR, and
**emails Blake** a digest. Graph + Gmail-OAuth (sections below) are dormant
fallbacks only.

### Go-live checklist (one-time, ~1 hour, no admin)

1. **Gmail App Password.** On **blake.e.ford@gmail.com** → Google Account →
   Security → enable **2-Step Verification** → **App passwords** → app "Mail" →
   copy the 16-char value. Confirm IMAP is on (Gmail Settings → Forwarding and
   POP/IMAP → **Enable IMAP**).
2. **Gmail label + filter.** Create a label **`Procurement/Alerts`**. Add a
   Gmail filter matching the portal sender domains **OR** `subject:[PROC-ALERT]`
   → **Apply label** `Procurement/Alerts`, **Never send to Spam**. (This is the
   `--imap-folder` the workflow reads.)

   > **Must be OR, not AND** (verified the hard way, 2026-07-05): forwarded
   > alerts arrive **from `beford@silverlinesleep.com`** with the
   > `[PROC-ALERT]` subject tag, while direct portal alerts arrive from a
   > portal domain **without** the tag. A filter requiring both matches
   > nothing, the label stays empty forever, and the daily ingest fetches 0.
   > In Gmail: Settings → Filters → Create new filter → put this in **"Has
   > the words"** (leave From empty):
   >
   > ```text
   > subject:"[PROC-ALERT]" OR from:(ionwave.net OR bonfirehub.com OR gobonfire.com OR demandstar.com OR bidnetdirect.com OR buyboard.com OR txsmartbuy.gov OR bidsync.com OR publicpurchase.com OR eunasolutions.com)
   > ```
   >
   > then check **Apply the label: Procurement/Alerts** and **Never send it
   > to Spam**. Also tick "Apply filter to matching conversations" so any
   > already-received alerts get labeled retroactively (the daily run looks
   > back 7 days).
3. **Point editable portals at Gmail.** On each portal whose notification
   address can be changed, set it to **blake.e.ford@gmail.com** and confirm the
   mattress/bedding commodity codes (NIGP 205, NAICS 337910) are selected.
4. **Business-only portals → Power Automate bridge.** For portals locked to
   `beford@silverlinesleep.com`, do **not** use an Outlook auto-forward rule
   (M365 blocks external auto-forwarding without admin). Instead, at
   **flow.microsoft.com** (signed in as the business account): keep an Outlook
   rule filing portal senders into a `Procurement Alerts` folder, then build an
   **Automated cloud flow**: trigger **"When a new email arrives in a folder
   (V3)"** → that folder → action **"Send an email (V2)"** to
   **blake.e.ford@gmail.com**, subject `[PROC-ALERT] <original subject>`, body
   that prints `From: <original sender>` and `Subject: <original subject>` on
   their own lines followed by the original body (so `unwrap_forwarded()`
   recovers the real portal sender). **Standard connectors only** — no
   premium/HTTP, so no admin license.
5. **Dead-man's-switch.** Create one free [healthchecks.io](https://healthchecks.io)
   check (period: 1 day, grace: 1 day); copy its **ping URL**.
6. **GitHub secrets** (Settings → Secrets and variables → Actions):
   - `GMAIL_ADDRESS` = blake.e.ford@gmail.com
   - `GMAIL_APP_PASSWORD` = the 16-char value from step 1
   - `NOTIFY_EMAIL_TO` = where to email you (optional; defaults to `GMAIL_ADDRESS`)
   - `HEALTHCHECK_URL` = the ping URL from step 5 (optional)
7. **Validate.** Actions → **Daily email-alert ingest (IMAP)** → **Run
   workflow**. Confirm it succeeds and, if there were new alerts, that a digest
   email arrives. Diagnose creds with:
   `GMAIL_ADDRESS=... GMAIL_APP_PASSWORD=... python tools/ingest_email.py --provider imap --imap-folder "Procurement/Alerts" --check`

Once steps 1, 6, and (3 and/or 4) are done, the channel is live — the workflow
runs daily and emails you any fit.

---

### Dormant fallback A - Power Automate digest to the business mailbox

(Pre-2026-06-27 stopgap, superseded by the live path above.) A scheduled Power
Automate flow that sends a digest of the `Procurement Alerts` folder to
`beford@silverlinesleep.com`. Kept only as a manual reference; it does not feed
the pipeline on its own.

## Previous path - route alerts to Gmail (disabled)

The older Gmail-forwarding setup is retained for history/fallback only:

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

### Previous operator decision (2026-06-18): forward Outlook → Gmail

Portal alerts currently arrive at the registered supplier mailbox
**`beford@silverlinesleep.com`** (Outlook), which the Gmail sweep cannot
see. Rather than re-pointing each portal's notification address to Gmail
(N portal logins; some portals only mail the registered account and a
free-mail contact can look unprofessional or need re-verification), the
chosen approach is a **single Outlook forwarding rule** — one action,
reversible, and it keeps the business identity on the portals intact.

**Outlook rule** (Settings → Rules → Add new rule):

- **Name:** `Procurement alerts → Gmail`
- **Condition:** *Sender address includes* any of —
  `ionwave.net`, `gobonfire.com`, `bonfirehub.com`, `demandstar.com`,
  `bidnetdirect.com`, `buyboard.com`, `txsmartbuy.gov`, `bidsync.com`,
  `publicpurchase.com`
- **Action:** *Forward to* `blake.e.ford@gmail.com` (use **Forward**, not
  Redirect, so original headers/links survive). Do **not** add a delete
  action — keep the originals of record in the business inbox.
- Check *Stop processing more rules*.

**On-demand sweep (no OAuth, only if forwarding works).** If alerts ever land
in a connected Gmail again, an assistant can run the same tested flow we
validated end-to-end on 2026-06-18:

1. Search the Gmail funnel for forwarded Outlook alerts. Because the
   Outlook rule uses **Forward** (not Redirect), Gmail sees the sender as
   `beford@silverlinesleep.com`; the original portal sender/domain is in
   the forwarded body. Use a query shaped like:

   ```text
   newer_than:8d from:beford@silverlinesleep.com (ionwave.net OR gobonfire.com OR bonfirehub.com OR demandstar.com OR bidnetdirect.com OR buyboard.com OR txsmartbuy.gov OR bidsync.com OR publicpurchase.com OR "Matching Bid Opportunities") -in:trash -in:spam
   ```

   If alerts are ever sent directly to Gmail, or if Outlook is changed to
   Redirect instead of Forward, then a `from:<portal-domain>` search is
   appropriate.
2. Map each alert to the `ingest_email.py` fixture shape
   (`id`, `sender`, `subject`, `date`, `body`).
3. `python tools/ingest_email.py --fixture <built>.json --dry-run` to
   preview, then drop `--dry-run`. The ingester gates each alert through
   `relevance.py`: `ACCEPT` rows are written to `bids/active/_pipeline.csv`,
   `REVIEW` rows are routed to Lead Radar (`leads/review/_lead_radar.csv`),
   and `REJECT` is dropped. (See `tools/README.md` → *Ingest routing* for
   `--leads` and `--review-target`.)
4. Triage the new `watching` rows (and any Lead Radar `reviewing` rows) and
   open a PR.

This needs no Gmail OAuth token or repo secrets — it relies on the
assistant's existing Gmail access. Mint the `GMAIL_*` secrets (above) only
when promoting this to the **unattended** weekly Action.

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
`.github/workflows/weekly_email_ingest.yml` (Mondays and Thursdays 13:30 UTC + manual
`workflow_dispatch`): it ingests, re-scores, runs the repo checks, and — if
`bids/active/_pipeline.csv` **or** `leads/review/_lead_radar.csv` changed —
opens a PR for human triage. The PR title/body state whether the run updated
active bids, Lead Radar, or both. It never auto-archives, auto-submits, or
pushes to `main`.

Operator digest: `.github/workflows/procurement_digest.yml` runs after the
scheduled ingests on Mondays and Thursdays at 14:30 UTC and posts one concise
update to the standing GitHub issue `Procurement ingest digest`.

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

### Forwarded alerts

Because the operator setup **forwards** portal alerts (the message sender is
the forwarding mailbox; the original alert is quoted in the body), the ingester
normalizes forwarded messages first: `unwrap_forwarded()` recovers the original
portal sender/subject from the quoted `From:`/`Subject:` header so a forwarded
alert is sourced and parsed exactly like a direct one (e.g. an IonWave
"Matching Bid Opportunities" digest still splits into one row per bid). This
runs on **every** provider path — Microsoft Graph, Gmail, and `--fixture` — so
the scheduled weekly Graph run handles forwarded items in the scanned folder
the same way the manual sweep did by hand. Both real provider paths prefer the
plain-text body (Graph sends `Prefer: outlook.body-content-type="text"`; Gmail
prefers `text/plain`), where the forwarded header sits on its own lines.

> Operational note: the scheduled run reads the `--graph-folder` you configure
> (default `"Procurement Alerts"`). Whatever rule populates that folder —
> filing the originals or forwarding copies into it — the alerts must actually
> land there for the weekly run to see them. Forwarded **and** direct alerts
> are both handled. (Fixtures in `tests/fixtures/email_alerts_forwarded_sample.json`.)
