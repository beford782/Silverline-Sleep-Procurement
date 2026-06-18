# Silverline Sleep Procurement Toolkit

Reusable operations toolkit for institutional and public-sector mattress
bidding. Holds vendor profiles, portal-registration checklists, bid
templates, and lightweight Python utilities for assembling procurement
packets.

This repository was separated from the DreamFinder consumer application
so the procurement-side workflows could evolve independently.

## Layout

```
bids/
  active/                Solicitations currently being pursued
    _pipeline.csv        Live opportunity tracker (one row per opportunity)
  archive/               Closed / awarded / no-bid / cancelled
    _pipeline_archive.csv  Archived rows moved out of active
  templates/             Reusable bid-response templates
portal-checklists/       Per-vendor portal-registration + commodity-code plans
sources/                 Machine-readable registry of opportunity sources
templates/               Blank intake forms (questionnaires, trackers)
vendor-profiles/         Vendor profiles in markdown and structured JSON
                         (vendor_profile.schema.json lives here too)
generated/
  examples/              Committed reference output (regenerated deterministically)
onboarding/              Internal onboarding notes for new vendors
procurement/             Domain overview and entry-point docs
tests/                   Stdlib unittest coverage for tools/
tools/                   Python utilities (stdlib-only where possible)
  hooks/                 Git hooks (e.g., pre-push fast-forward guard)
build/                   Default output of tools/ (gitignored, do not commit)
```

## Common workflows

### 1. Onboard a new vendor

1. Copy `templates/mattress_bid_setup_questionnaire.csv` and have the
   vendor fill in the **Your Answer** column.
2. Run the packet generator (writes to `build/generated/` by default,
   which is gitignored):
   ```sh
   python tools/generate_procurement_packet.py path/to/answers.csv \
       --vendor "Vendor Name"
   ```
   Add `--generated-date YYYY-MM-DD` to pin the timestamp (used for
   committed examples), or `--answered-only` to drop blank rows.
3. Save the answered CSV under `vendor-profiles/<vendor>_questionnaire.csv`.
4. Author a structured `vendor-profiles/<vendor>.profile.json` (see
   `vendor-profiles/continental_silverline.profile.json` for shape).
5. Validate:
   ```sh
   python tools/validate_vendor_profile.py vendor-profiles/<vendor>.profile.json
   ```
6. Capture the narrative profile in `vendor-profiles/<vendor>.md`.

### 2. Prepare a portal-registration plan

1. Read `portal-checklists/continental_silverline_portal_setup.md` as a
   reference.
2. Author `portal-checklists/<vendor>_portal_setup.md`, listing the
   portals to register on, commodity-code groups, saved searches, and
   the registration field tracker.

### 3. Stand up a bid response

1. Add the opportunity to the pipeline:
   ```sh
   python tools/pipeline.py add \
       --source "Texas ESBD" \
       --buyer "Texas Facilities Commission" \
       --solicitation-number "IFB 529-XYZ" \
       --title "Dormitory mattresses pilot" \
       --due-date 2026-06-15
   ```
2. Render a starter draft from the pipeline row + a vendor profile:
   ```sh
   python tools/draft_bid_response.py <opportunity-id> \
       --vendor vendor-profiles/continental_silverline.profile.json
   ```
   The draft lands at `build/drafts/<opportunity-id>_draft.md`
   (gitignored). It pre-fills the bid-template table, product-fit
   intersection (vendor `products: yes` ∩ opportunity primary
   products), compliance-availability lines, delivery-fit notes, the
   Required Documents checklist, and a decision suggestion derived
   from `risk_level`.
3. Promote the generated draft into active bid work:
   ```sh
   python tools/promote_draft.py <opportunity-id>
   ```

   This writes `bids/active/<opportunity-id>.md` and refuses to
   overwrite an existing active bid file unless `--force` is passed.
4. Edit the promoted markdown's prose, open questions, and final
   decision by hand. The draft is regenerable; the committed markdown
   is the operator's source of truth.
5. On award/decline, archive both:
   ```sh
   python tools/pipeline.py move-to-archive <opportunity-id>
   git mv bids/active/<opportunity-id>.md bids/archive/<opportunity-id>.md
   ```

   (The corresponding `build/drafts/<opportunity-id>_draft.md` can be
   left in `build/`; it's gitignored and regenerable from the archived
   pipeline row.)

### 4. Work the opportunity pipeline

```sh
python tools/pipeline.py list             # active rows, sorted by due_date
python tools/dashboard.py                 # operator dashboard for active work
python tools/pipeline.py summary          # counts by status, source, risk
python tools/pipeline.py score --dry-run  # preview keyword-driven fit/risk
python tools/pipeline.py score            # write the recomputed values
python tools/workflow_check.py            # catch CSV/markdown/status drift
```

The keyword vocabularies live at the top of `tools/pipeline.py` and
are deliberately readable — tweak `POSITIVE_KEYWORDS`,
`CAUTION_KEYWORDS`, and `STRONG_CAUTION` to match the institutional
mattress vocabulary you actually see in solicitations.

### 5. Federal opportunity ingestion (SAM.gov)

`tools/ingest_sam.py` pulls federal contract opportunities from the
SAM.gov public API into the active pipeline. Stdlib only — no new
dependencies.

```sh
export SAM_API_KEY=...    # never commit; sign up at sam.gov

python tools/ingest_sam.py \
    --title "mattress" \
    --posted-from 2026-05-01 \
    --posted-to 2026-05-14 \
    [--naics-code 337910] \
    [--notice-type o] \
    [--response-deadline-after 2026-05-14] \
    [--dry-run]

# NAICS 337910 = mattress manufacturing. Use it to drop most false
# positives (concrete mattresses for civil works, aircraft hardware
# under different NAICS, services-only postings, etc.).
#
# By default the ingester filters out past-due opportunities (rdlfrom
# defaults to today). Pass --include-past-due if you want them back in.
```

Behavior:

- Fetches all matching opportunities (paginated, capped by
  `--max-pages`).
- Maps documented SAM.gov fields onto the pipeline schema; never
  pulls contact PII.
- Dedupes against both `bids/active/_pipeline.csv` and
  `bids/archive/_pipeline_archive.csv` by `opportunity_id` and
  `solicitation_number`, so previously-closed no-bids are reported as
  archive dupes instead of being re-ingested into active. Re-running
  with an overlapping date range is safe.
- `--dry-run` previews what would be added without writing.
- **Gated by `tools/relevance.py`**: each record is classified
  ACCEPT / REVIEW / REJECT (NAICS 337910 / PSC 7210 count as strong
  mattress signals). Rejects are not written; reviews are kept with a
  human-confirm flag.
- HTTP 404 from SAM.gov is treated as "no results" per the API's
  documented semantics — that's a normal exit-0 outcome when your
  filters match nothing in the date range.
- The keyword scoring vocabulary in `tools/pipeline.py` was tuned
  against real federal-procurement titles. Caution keywords like
  `aircraft`, `concrete`, `inspection services`, `refinish`,
  `reupholster`, and `overseas` catch the false positives we've seen
  in actual SAM.gov mattress ingests (aviation hardware, civil works,
  services-only postings, refurbishment, out-of-geography work).

`sources/procurement_sources.json` is the machine-readable list of
where opportunities surface. SAM.gov ingestion is automated by
`tools/ingest_sam.py`. State/local portals still require operator
review, but portal CSV exports can be imported when a mapping exists.
ESBD is currently mapped via `configs/portal_csv/esbd.json` and
`tools/ingest_portal_csv.py`; Beacon Bid, Bonfire, IonWave, and
cooperatives still rely on portal-side notifications and manual
`tools/pipeline.py add` rows until mappings are added.

**Scheduled run.** `.github/workflows/weekly_sam_ingest.yml` runs the
ingest every Monday at 13:00 UTC (08:00 Houston CDT) and on manual
`workflow_dispatch`. It scores the new rows and, if
`bids/active/_pipeline.csv` changed, opens a PR for human triage. It
never auto-archives, never auto-submits, and never pushes to `main`.
Requires the `SAM_API_KEY` repo secret to be set
(*Settings → Secrets and variables → Actions*); the workflow fails
fast with a clear error if it is missing.

### 6. Track commodity codes

Commodity-code groups live alongside each vendor's
`portal-checklists/<vendor>_portal_setup.md`. Keep the canonical term
list there so all portals (CMBL, Bonfire, IonWave, Beacon Bid, etc.)
get the same vocabulary.

### 7. Weekly state/local portal review and CSV import

`tools/source_review.py` turns `sources/procurement_sources.json` into
a dated Markdown checklist of the non-API portals an operator needs to
walk manually each week (the state opportunity boards — Texas ESBD,
Oklahoma OMES, Louisiana LaPAC, Mississippi MAGIC, Arkansas ARBuy, New
Mexico SPD — plus City of Houston Beacon Bid, Harris County Bonfire,
and Houston ISD IonWave, with the universities and cooperatives on the
monthly cadence). SAM.gov and any future `has_api: true` source is
always excluded; it's handled by `tools/ingest_sam.py` and the
scheduled GitHub Action.

The generated worksheet lands at
`build/portal_reviews/<date>_<cadence>.md` (gitignored, regenerable).
Walk each portal's UI / saved searches, record anything worth
pursuing via `python tools/pipeline.py add ...` or, for portals with
CSV export mappings, `python tools/ingest_portal_csv.py ...`. Then
discard the worksheet. The registry and pipeline CSVs are the
committed source of truth.

```sh
# Default: weekly cadence (state boards TX/OK/LA/MS/AR/NM + Houston
# Beacon Bid, Harris County Bonfire, Houston ISD IonWave).
python tools/source_review.py

# Monthly cadence (3 Texas university systems + 6 cooperatives).
python tools/source_review.py --cadence monthly

# Everything except SAM.gov (or any API-driven source).
python tools/source_review.py --cadence all

# Preview without writing a file.
python tools/source_review.py --dry-run

# Pin the date stamp (useful for reproducible reviews).
python tools/source_review.py --date 2026-05-18

# What cadence buckets are present in the registry?
python tools/source_review.py --list-cadences
```

ESBD CSV import:

```sh
python tools/portal_csv_mapping.py path/to/portal-export.csv \
    --source "Portal Name"

python tools/ingest_portal_csv.py path/to/esbd-export.csv \
    --mapping configs/portal_csv/esbd.json \
    --dry-run

python tools/ingest_portal_csv.py path/to/esbd-export.csv \
    --mapping configs/portal_csv/esbd.json
```

The importer fails by default if a mapped date cannot be parsed, so a
bad deadline cannot quietly enter the pipeline as blank. Fix the CSV,
add the date format to the mapping, or pass `--allow-bad-dates` only
when you have manually confirmed the affected rows.

For a new portal export, use `tools/portal_csv_mapping.py --write` to
create a starter config under `configs/portal_csv/`, review the
suggested fields, then run `tools/ingest_portal_csv.py --dry-run`
against that mapping.

### 8. State/local email-alert ingestion

The state/local and cooperative portals have **no public RSS feed or
opportunity API** (verified June 2026), so they can't be polled like
SAM.gov and must never be scraped. The compliant, automatable channel is
the **commodity/NIGP email alert** each portal sends to a registered
supplier. `tools/ingest_email.py` reads those alerts from the alert
mailbox and turns them into `watching` pipeline rows — automating the
manual portal walk for the email-notification sources. Two backends, both
stdlib `urllib`: **Outlook / Microsoft 365 via the Microsoft Graph API**
(`--provider graph`, the tool default) and **Gmail via the Gmail REST API**
(`--provider gmail`).

> **Recommended operator path (no Azure admin):** route the portal alerts
> to a Gmail address and ingest via `--provider gmail` (or an on-demand
> assistant sweep). The Graph backend needs a tenant-admin Mail.Read
> consent; see [`docs/email_ingest_setup.md`](docs/email_ingest_setup.md).

```sh
# Offline / test (no creds, no network)
python tools/ingest_email.py --fixture tests/fixtures/email_alerts_sample.json --dry-run

# Live Outlook/M365 (Graph app-only creds in env)
GRAPH_TENANT_ID=... GRAPH_CLIENT_ID=... GRAPH_CLIENT_SECRET=... GRAPH_MAILBOX=beford@silverlinesleep.com \
  python tools/ingest_email.py --graph-folder "Procurement Alerts" --since-days 8 --dry-run

# Live Gmail (OAuth refresh-token creds in env)
GMAIL_CLIENT_ID=... GMAIL_CLIENT_SECRET=... GMAIL_REFRESH_TOKEN=... \
  python tools/ingest_email.py --provider gmail --query 'label:Procurement/Alerts newer_than:8d' --dry-run
```

Behavior:

- Maps each alert email onto the pipeline schema; dedupes against active
  **and** archive by `opportunity_id` (a stable slug of source + title +
  a short hash of the portal link), so re-running over an overlapping
  window is safe.
- **Gated by `tools/relevance.py`**: every parsed alert is classified
  ACCEPT / REVIEW / REJECT. Non-mattress noise (broad furniture/office
  digests, registration confirmations) is rejected and never written;
  ambiguous items are kept with a `next_action` flag for human review.
  `--reject-log PATH` optionally records rejects for tuning.
- The parser is **generic and best-effort**: title (subject, prefixes
  stripped), portal link, and due date; `buyer`/`location` may be blank.
  Always verify ingested rows against the portal. Add per-sender adapters
  as real samples are captured.
- One-time setup (portal alert subscriptions + an Azure app registration
  for Graph, or a Gmail OAuth token) is in
  [`docs/email_ingest_setup.md`](docs/email_ingest_setup.md).

**Scheduled run.** `.github/workflows/weekly_email_ingest.yml` runs every
Monday at 13:30 UTC and on manual `workflow_dispatch`, ingests (Graph),
re-scores, runs the repo checks, and opens a PR for human triage if the
active pipeline changed. It never auto-archives, auto-submits, or pushes
to `main`. Requires the `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`,
`GRAPH_CLIENT_SECRET`, and `GRAPH_MAILBOX` repo secrets; it fails fast if
any are missing.

### 9. RSS/feed ingestion (Bonfire portals, etc.)

`tools/ingest_rss.py` pulls open-opportunity RSS/Atom feeds through the
relevance filter into the pipeline — the cleanest no-scraping web channel.
The best feeds are **Bonfire per-portal** open-opportunity feeds
(`https://{agency}.bonfirehub.com/opportunities/rss`), which are public,
token-free, and contain *actual solicitations* (not news). Configure feeds
in `configs/feeds.json` (see `configs/feeds.example.json`).

```sh
python tools/ingest_rss.py --feeds-config configs/feeds.json --dry-run
python tools/ingest_rss.py --feed https://harriscountytx.bonfirehub.com/opportunities/rss --source "Bonfire: Harris County"
```

- Web/RSS items are held to a higher bar: they must carry a procurement
  cue (RFP/bid/solicitation/…) to ACCEPT, and known non-procurement hosts
  (Quora/Reddit/social/retail) are rejected — so news/catalog noise stays
  out. Google Alerts feeds *can* be added but are low-signal (mostly news
  even when scoped); prefer Bonfire/portal feeds.
- Scheduled by `.github/workflows/weekly_rss_ingest.yml` (Mon 13:45 UTC +
  manual). No secrets — the feeds are public. Opens a PR on change.

## Tools

Lightweight Python utilities, all stdlib-only where possible:

| Script | Purpose |
| --- | --- |
| `tools/pipeline.py` | Manage `bids/active/_pipeline.csv`: add, list, summary, score, move-to-archive |
| `tools/dashboard.py` | Print a read-only operator dashboard for active deadlines, ownership gaps, scoring gaps, risk, and drafts ready to promote. |
| `tools/draft_bid_response.py` | Combine an opportunity row with a vendor profile to render a starter response markdown under `build/drafts/` |
| `tools/promote_draft.py` | Promote a generated draft into `bids/active/<opportunity-id>.md` with overwrite and archive-collision checks. |
| `tools/ingest_sam.py` | Pull federal opportunities from the SAM.gov public API (stdlib `urllib`) into the pipeline. Requires `SAM_API_KEY`. |
| `tools/ingest_portal_csv.py` | Import operator-downloaded portal CSV exports using JSON column mappings, currently including ESBD. |
| `tools/ingest_email.py` | Ingest portal commodity/NIGP email alerts into the pipeline (stdlib `urllib`). Default backend Outlook/M365 via Microsoft Graph (`GRAPH_*` secrets); Gmail backend optional (`GMAIL_*`). See `docs/email_ingest_setup.md`. |
| `tools/ingest_rss.py` | Ingest RSS/Atom feeds (Google Alerts, Bonfire portal feeds, RFPMart) into the pipeline, gated by the relevance filter. Configure feeds via `configs/feeds.json` (see `configs/feeds.example.json`). |
| `tools/portal_csv_mapping.py` | Inspect a portal CSV export and write a starter mapping JSON for `ingest_portal_csv.py`. |
| `tools/source_review.py` | Generate an operator portal-review checklist from the source registry. Writes to `build/portal_reviews/` (gitignored). |
| `tools/generate_procurement_packet.py` | CSV questionnaire → markdown + printable HTML packet |
| `tools/validate_vendor_profile.py` | Validate `vendor-profiles/*.profile.json` against the schema |
| `tools/workflow_check.py` | Check pipeline rows against bid markdown files for status drift, missing active drafts, stale reviews, and archive mismatches. |
| `tools/relevance.py` | Central mattress-relevance filter (ACCEPT/REVIEW/REJECT) that every ingester gates on, so non-mattress noise (furniture/office digests, concrete/air mattresses, registration emails) never enters the pipeline. |

Run the test suite with:

```sh
python -m unittest discover -s tests
```

See `tools/README.md` for the full tool inventory.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
