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

## Recommended path - Power Automate digest (no Azure admin)

Current operator decision (2026-06-24): use Microsoft Power Automate instead
of the scheduled Microsoft Graph workflow. Portal alerts remain in Outlook
under the `Procurement Alerts` folder, and a scheduled Power Automate flow sends
a digest to `beford@silverlinesleep.com`.

Power Automate flow target:

- **Trigger:** scheduled recurrence, Monday and Thursday.
- **Action:** Office 365 Outlook **Get emails (V3)**.
- **Folder:** `Procurement Alerts`.
- **Fetch Only Unread Messages:** `No`.
- **Top:** `50`.
- **Action:** Office 365 Outlook **Send an email (V2)**.
- **To:** `beford@silverlinesleep.com`.
- **Subject:** `Procurement Alerts digest - @{formatDateTime(utcNow(),'yyyy-MM-dd')}`.
- **Body:** ideally one combined digest containing sender, subject, received
  date, and body preview/link for each message. A one-email-per-alert flow is
  acceptable temporarily while the combined digest expression is tuned.

Save and test the flow after configuration. Confirm that messages already in
`Procurement Alerts` are included because the flow is intentionally not limited
to unread mail.

The scheduled GitHub Graph workflow is intentionally paused and available only
as a manual fallback. Do not chase Azure Graph secrets unless that strategy is
explicitly reopened.

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
