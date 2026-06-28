# Awareness System Design - getting opportunities to Blake

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-27
- **Problem:** The email-alert channel (the majority of registered portals -
  IonWave, DemandStar, BidNet, BuyBoard, Texas ESBD, the co-ops, NM-SPD - which
  have no RSS/API) was not reaching the pipeline OR Blake. Both automated email
  paths were dead: Microsoft Graph (needs Azure admin Blake does not have) and
  Gmail OAuth (broken refresh token). RSS (16 Bonfire feeds) and SAM.gov work.
- **Method:** Multi-agent design - 6 independent architectures from distinct
  seeds, each adversarially scored on reliability / setup-effort / maintenance /
  compliance / coverage / notification / cost, then synthesized. 13 agents.

> **Operator decision (2026-06-27):** the synthesized design recommends a
> Telegram push; **Blake chose plain email-to-self** for the notification
> channel instead. We implement that via **Gmail SMTP (`smtplib`) reusing the
> same App Password** - no new credential, no Telegram bot. Everything else in
> the design (App-Password IMAP ingestion, the Power Automate bridge, and the
> three reliability watchdogs) is adopted as-is. References to "Telegram push"
> below map to "email-to-self" in what we build.

---

## Recommended system: "Silverline Awareness Bridge"

**Gmail App-Password IMAP ingest + email-to-self notification, with a Power
Automate connector-send for business-only portals.**

How an opportunity flows:

1. A portal's commodity-code alert email lands in **blake.e.ford@gmail.com** -
   either because that is the portal's notification contact, or because a Power
   Automate flow re-sent it from the business mailbox.
2. On a daily GitHub Actions cron, a new `tools/ingest_email.py --provider imap`
   reader logs into `imap.gmail.com:993` with a **self-issued Gmail App
   Password** (stdlib `imaplib`, no admin, no token expiry), pulls the look-back
   window, and runs each message through the unchanged
   `unwrap_forwarded()` -> `split_ionwave_digest()` -> `relevance.classify()`
   chain.
3. ACCEPT writes to `bids/active/_pipeline.csv`, REVIEW to
   `leads/review/_lead_radar.csv`; the workflow opens the usual `auto/*` PR.
4. The moment a fit is written, a notify step **emails Blake** a distilled alert
   (title, source, due date, portal link, PR URL). A failure or a missed run
   also emails him.

**Exact ingestion mechanism:** Gmail IMAP over TLS with a Google App Password
(secrets `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD`). **Exact notification:** email
via Gmail SMTP (`smtplib`, same App Password) to Blake.

## Why this design

- All six designs converged on **App-Password IMAP** for ingestion - it beats
  both dead paths: no Azure admin (vs Graph), no OAuth consent-screen
  verification, and no refresh-token expiry (vs Gmail OAuth). It just keeps
  working. `imaplib` is stdlib, matching the toolkit's dependency-free rule.
- **Business-only portals:** do NOT rely on an Outlook auto-forward rule - M365
  blocks external auto-forwarding by default and Blake cannot lift that without
  admin (the same wall that killed Graph). A standard-connector Power Automate
  **"Send an email (V2)"** is *not* treated as auto-forwarding and is not
  blocked.

### Scoreboard (weighted /60)
| Design | Total | Verdict |
|---|---|---|
| Gmail-IMAP hub + ntfy push | 40 | recommend |
| Phone-First (App-Password IMAP + Telegram) | 39 | viable |
| Gmail-Funnel (self-monitoring) | 38 | viable |
| Power Automate Bridge + Gmail-read + ntfy | 38 | viable |
| Gmail Hub (durable personal-OAuth) | 36 | viable |
| Gmail-hub loop (OAuth + GitHub Mobile push) | 32 | viable |

The top two were ingestion-identical; the synthesis took the winning IMAP
ingest and the safer push (rejecting ntfy, whose "private topic" is
obscurity-only). Blake then chose email-to-self over Telegram.

## What Blake sets up once (no admin, ~1 hour)

1. **Gmail App Password.** blake.e.ford@gmail.com -> Security -> enable
   2-Step Verification -> App passwords -> Mail -> copy the 16-char value.
   Confirm IMAP is on (Gmail Settings -> Forwarding and POP/IMAP -> Enable IMAP).
2. **Point portals at Gmail where editable.** On each portal whose notification
   address can be changed, set it to blake.e.ford@gmail.com and confirm
   mattress/bedding codes are selected.
3. **Power Automate bridge for business-only portals.** At flow.microsoft.com
   (as beford@silverlinesleep.com): keep the Outlook rule that files portal
   senders into the "Procurement Alerts" folder; create an Automated cloud flow,
   trigger "When a new email arrives in a folder (V3)" -> Procurement Alerts ->
   action "Send an email (V2)" to blake.e.ford@gmail.com, subject
   `[PROC-ALERT] <original subject>`, body printing `From: <original sender>`
   and `Subject: <original subject>` on their own lines followed by the original
   body (so `unwrap_forwarded()` recovers the real portal sender). Standard
   connectors only - no premium/HTTP, no admin license.
4. **Gmail label.** One Gmail filter on the portal sender domains plus
   `subject:[PROC-ALERT]` -> apply label `Procurement/Alerts`, Never send to Spam.
5. **Dead-man's-switch.** One free healthchecks.io check; copy its ping URL
   (catches the GitHub cron itself silently stopping).
6. **GitHub secrets** (Settings -> Secrets and variables -> Actions):
   `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `NOTIFY_EMAIL_TO` (where to email
   Blake), `HEALTHCHECK_URL`.
7. **Validate.** Actions -> Run workflow once; confirm a test alert email arrives.

## What I build (code/CI) - smallest first, each independently shippable

1. **`--provider imap` in `tools/ingest_email.py`** (~40 lines): `imaplib.IMAP4_SSL`,
   login with `GMAIL_ADDRESS`/`GMAIL_APP_PASSWORD`, `SEARCH SINCE <today-7d>`,
   return the same `{id, sender, subject, date, body}` dict the Graph/Gmail
   paths already emit. Ships with a parse fixture so the existing
   `unwrap_forwarded`/`split_ionwave_digest`/`relevance.classify` chain is
   exercised unchanged. **(building first)**
2. **`tools/notify_push.py`** (stdlib `smtplib`/`email`): send Blake one email
   per new ACCEPT row (title, source, due date, portal link, PR URL) and one
   batched email for new REVIEW/Lead Radar rows. Non-fatal - a notify error
   never fails the job.
3. **`.github/workflows/daily_email_ingest.yml`** (clone the proven step order
   from the paused `weekly_email_ingest.yml`): daily cron + `workflow_dispatch`;
   fail-fast secret check -> `ingest_email.py --provider imap --since-days 7` ->
   diff/re-score/CI -> open `auto/*` PR if a CSV changed -> `notify_push.py` ->
   curl the `HEALTHCHECK_URL` on success. A **7-day** SINCE window (not 2)
   survives cron slippage; dedup keys keep the overlap idempotent.
4. **`if: failure()` notify + issue step**: on any run exception, email Blake in
   addition to the existing failure issue.
5. **Zero-message watchdog** (weekly): if the IMAP reader fetched 0 messages
   across the last >=2 runs AND no `[PROC-ALERT]` mail arrived, raise a loud
   issue + email - distinguishes "quiet market" from "broken pipe."
6. **Docs:** update `docs/email_ingest_setup.md` with the App-Password, email,
   and Power Automate steps; mark Graph/Gmail-OAuth providers as dormant fallbacks.

## Reliability & fallbacks

- **Stays loud three ways.** (a) `if: failure()` emails Blake on any run that
  starts and throws (auth break, etc.). (b) The **zero-message watchdog** catches
  the silent case where runs go green but no alerts arrive (broken forward,
  renamed label, dropped portal contact). (c) The **healthchecks.io
  dead-man's-switch** is the only check external to GitHub - it emails Blake if
  the scheduled run never starts at all (GitHub auto-disables crons after ~60
  days of repo inactivity; a never-started run produces no failure event). These
  three close the "successful empty run = real silent miss" gap.
- **Single best fallback if the email bridge breaks.** If App-Password IMAP auth
  dies (2FA disabled, Google revokes it, future deprecation), fall back to the
  already-coded `--provider gmail` OAuth path on the same mailbox - same label,
  same parser, only a different credential. The paused Graph workflow remains a
  last resort if Blake ever gains Azure admin.
- **Latency:** daily poll + 7-day window means a fit appears within ~24h;
  idempotent dedup means a skipped day self-heals on the next run.

## Honest limitations

- **Non-editable portal address that also can't reach the Power Automate folder**
  (e.g. a brand-new co-op from an unrecognized domain) is never captured and
  looks identical to a quiet week. Onboarding a new portal still means manually
  adding its sender domain to the Gmail filter and the Outlook rule.
- **Free-mail contact friction.** Some portals may reject a personal `gmail.com`
  supplier contact; those stay on the business mailbox + Power Automate path.
- **Parser thinness.** On a layout change the title still comes from the subject,
  but buyer/due-date/solicitation-number may go blank, and an unrecognized
  multi-bid digest can collapse to one row. Honest degradation (Blake is still
  notified and verifies on the portal), lossy until a per-sender adapter is added.
- **Tenant lockdown.** If silverlinesleep.com is MSP-managed with a Power
  Platform DLP policy disabling the standard Outlook connector, the
  business-only bridge has no no-admin path; coverage narrows to portals that
  accept the Gmail address directly.
- **Attachment-only detail.** A bare "Bid Notification" whose mattress content
  lives only in a PDF attachment can score REJECT, since `relevance.classify()`
  reads subject/body text only.

---

### Scope note
Design record only. Implementation ships as separate scoped PRs (build list
above). PII (App Password, secrets) stays out of version control.
