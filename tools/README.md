# Tools

Lightweight Python utilities for the procurement toolkit.

## Procurement utilities

| Script | Stdlib only? | Purpose |
| --- | --- | --- |
| `pipeline.py` | yes | Manage the opportunity pipeline at `bids/active/_pipeline.csv`. Subcommands: `add`, `list`, `summary`, `score`, `move-to-archive`. |
| `lead_radar.py` | yes | Manage the **Lead Radar** at `leads/review/_lead_radar.csv` — broad upstream opportunities (co-op vehicles, FF&E, dorm/student-housing, correctional, shelter, public-health residential) that are not yet confirmed mattress bids. Subcommands: `summary`, `list`, `add`, `archive`, `promote`. `promote` is the only path into the active bid pipeline and requires an explicit human `--confirmed-products`. |
| `dashboard.py` | yes | Print a read-only operator dashboard for active deadlines, ownership gaps, scoring gaps, risk, and drafts ready to promote. |
| `draft_bid_response.py` | yes | Render a starter bid response by combining one pipeline row (looked up by `opportunity_id` in active first, then archive) with a vendor profile JSON. Output is markdown under `build/drafts/` (gitignored) so generated content never collides with committed bid markdown. |
| `promote_draft.py` | yes | Promote `build/drafts/<opportunity-id>_draft.md` into `bids/active/<opportunity-id>.md` with overwrite and archive-collision checks. |
| `ingest_sam.py` | yes | Pull federal opportunities from SAM.gov's public API (`api.sam.gov/opportunities/v2/search`) into the pipeline. Stdlib HTTPS via `urllib.request`. Requires `SAM_API_KEY` env var. Sweep by `--title`, `--naics-code` (e.g. 337910), and/or `--psc` (e.g. 7210/7105). Gated by `relevance.py`: `ACCEPT` rows write to `bids/active/_pipeline.csv`; `REVIEW` rows route to Lead Radar (`--leads`, default `leads/review/_lead_radar.csv`); `REJECT` is dropped. `--review-target` overrides routing. Dedupes by `solicitation_number` + `opportunity_id` (leads also deduped against Lead Radar + active/archive). |
| `ingest_portal_csv.py` | yes | Import an operator-downloaded portal CSV export into the active pipeline using a JSON column mapping such as `configs/portal_csv/esbd.json`. |
| `ingest_email.py` | yes | Ingest portal commodity/NIGP email alerts from the alert mailbox. Stdlib HTTPS via `urllib.request`. Two backends: `--provider graph` (Outlook/M365 via Microsoft Graph, app-only OAuth; `GRAPH_TENANT_ID`/`GRAPH_CLIENT_ID`/`GRAPH_CLIENT_SECRET`/`GRAPH_MAILBOX`) and `--provider gmail` (Gmail REST, refresh-token; `GMAIL_*`). `--fixture` for offline use. Generic title/link/due-date parser; dedupes by `opportunity_id`. Gated by `relevance.py`: `ACCEPT` rows write to `bids/active/_pipeline.csv`; `REVIEW` rows route to Lead Radar (`--leads`, default `leads/review/_lead_radar.csv`); `REJECT` is dropped. `--review-target` overrides routing. See `docs/email_ingest_setup.md`. |
| `ingest_rss.py` | yes | Ingest RSS 2.0 / Atom feeds (Google Alerts, Bonfire `/opportunities/rss`, RFPMart, etc.). Stdlib `urllib` + `xml.etree`; unwraps Google Alerts redirect links. Feeds via `--feed`/`--source`, `--feeds-config` (see `configs/feeds.example.json`), or `--fixture`. Gated by `relevance.py`: `ACCEPT` rows write to `bids/active/_pipeline.csv`; `REVIEW` rows route to Lead Radar (`--leads`, default `leads/review/_lead_radar.csv`); `REJECT` is dropped. `--review-target` overrides routing. Dedupes by `opportunity_id` (leads also deduped against Lead Radar + active/archive). |
| `portal_csv_mapping.py` | yes | Inspect a portal CSV export and write a starter mapping JSON for `ingest_portal_csv.py`. |
| `generate_procurement_packet.py` | yes | Reads a questionnaire CSV, writes a markdown packet and printable HTML. Default output dir is `build/generated/` (gitignored). |
| `validate_vendor_profile.py` | yes | Validates `vendor-profiles/*.profile.json` against `vendor-profiles/vendor_profile.schema.json`. Walks the schema at runtime; no parallel hardcoded rules. |
| `workflow_check.py` | yes | Check pipeline rows against bid markdown files for status drift, missing active drafts, stale reviews, and archive mismatches. |
| `relevance.py` | yes | Central mattress-relevance classifier. `classify(text)` returns ACCEPT / REVIEW / REJECT with confidence, matched terms, and reasons (whole-word/phrase matching; NAICS 337910 / PSC 7210 aware; six-state geography demotion). Every ingester gates on it so non-mattress noise never reaches the pipeline. CLI: `python tools/relevance.py "text"`. |

### Work the opportunity pipeline

```sh
python tools/pipeline.py add \
    --source "Texas ESBD" \
    --buyer "Texas Facilities Commission" \
    --solicitation-number "IFB 529-XYZ" \
    --title "Dormitory mattresses pilot" \
    --due-date 2026-06-15

python tools/pipeline.py list             # active rows, sorted by due_date
python tools/dashboard.py                 # active-work operator dashboard
python tools/pipeline.py summary          # counts by status, source, risk
python tools/pipeline.py score --dry-run  # preview keyword-driven fit/risk
python tools/pipeline.py score            # write recomputed values
python tools/workflow_check.py            # check CSV/markdown workflow drift
python tools/pipeline.py move-to-archive <opportunity-id>
```

Flags worth knowing:

- `--active PATH` / `--archive PATH` — override the default CSV
  locations (`bids/active/_pipeline.csv` /
  `bids/archive/_pipeline_archive.csv`).
- `--overwrite` (on `add`) — replace a row with the same
  `opportunity_id` instead of refusing.
- `--dry-run` (on `score`) — print the would-be changes and exit
  without touching the CSV.

The `score` subcommand delegates `fit_score` to `relevance.classify`
(`tools/relevance.py`), so the pipeline scores a row the same whole-word
way every ingest channel does — re-scoring never clobbers the
relevance-derived score, and there are no substring false-fires. The
tunable mattress vocabulary lives in `relevance.py`.

`fit_score` is numeric (`0` to `100`). `risk_level` is one of `low`,
`medium`, or `high` and describes product/spec fit risk. Procurement
readiness is tracked separately:

- `procurement_risk`: `low`, `medium`, `high`, or `blocker`
- `gate_status`: `triage`, `blocked`, `bid_ready`, `drafting`, `submitted`, or `closed`
- `compliance_blocker`: semicolon-separated blocker tokens such as
  `sam_registration_pending`, `portal_access_pending`, or `specs_pending`

A strong product fit can still be blocked from bidding. For example,
`fit_score=100` with `procurement_risk=blocker` means the opportunity is
relevant, but a procurement gate must be cleared before bid work proceeds.

### Capture upstream leads (Lead Radar)

The active pipeline (`bids/active/_pipeline.csv`) is kept strict: **only
confirmed mattress / product-fit bids belong there.** But much institutional
mattress demand never appears as a standalone "mattress" RFP — it is bought
through broad cooperative / vendor-pool / IDIQ vehicles (BuyBoard, TIPS,
Choice Partners, Sourcewell, HGACBuy, OMNIA), school-furniture / FF&E
contracts, dorm / student-housing, correctional / detention supply,
shelter / emergency supply, and public-health residential contracts.

**Lead Radar** (`leads/review/_lead_radar.csv`) is a separate, looser layer
for those broad upstream signals. It makes the hidden market visible without
polluting the clean bid pipeline.

```sh
python tools/lead_radar.py add \
    --source "IonWave" \
    --buyer "Region 6 ESC (EPIC6)" \
    --solicitation-number "RFP 16.26" \
    --title "School Furniture & Related Services" \
    --lead-type broad_furniture_ffe \
    --trigger-terms "furniture; ff&e" \
    --due-date 2026-07-15

python tools/lead_radar.py list      # review leads, sorted by due_date
python tools/lead_radar.py summary   # counts by status, source, lead_type
python tools/lead_radar.py archive <lead-id> --status no-fit --note "furniture only"

# The ONLY path from a lead into the active bid pipeline. A human must
# state the confirmed product fit; broad leads never auto-promote.
python tools/lead_radar.py promote <lead-id> \
    --confirmed-products "mattresses; bed frames"
```

`lead_type` is one of `co-op_contract_vehicle`, `broad_furniture_ffe`,
`dorm_student_housing`, `correctional_detention`, `shelter_emergency`,
`public_health_residential`, `awarded_contract_watch`, `other`. `status` is
one of `watching`, `reviewing`, `promoted`, `archived`, `no-fit`, `stale`.

`promote` copies the lead into `bids/active/_pipeline.csv` as a `watching`
row (deduped by generated `opportunity_id`), records the human-confirmed
products, and marks the lead `promoted` — it never deletes the lead, and it
refuses to run without `--confirmed-products`.

#### Ingest routing (email + RSS)

Lead Radar is intentionally **not** the bid pipeline. It holds `REVIEW`-band
opportunities that may indicate future or indirect mattress spend, while the
active pipeline stays limited to confirmed product-fit bid opportunities.

`tools/ingest_email.py` and `tools/ingest_rss.py` both gate every parsed item
through `relevance.py` and route by decision band:

| Relevance band | Destination | Notes |
| --- | --- | --- |
| `ACCEPT` | `bids/active/_pipeline.csv` | Clear mattress / product-fit signal. |
| `REVIEW` | `leads/review/_lead_radar.csv` | Broad / ambiguous upstream signal — **default route**. |
| `REJECT` | *(dropped)* | Never enters the active pipeline **or** Lead Radar. |

Routing flags (both ingesters):

- `--leads PATH` — Lead Radar CSV the `REVIEW` rows are written to
  (default `leads/review/_lead_radar.csv`).
- `--review-target {leads,active,reject-log}` — override where `REVIEW`-band
  items go. `leads` is the default; `active` is the legacy/debug behavior
  (writes the flagged row straight to the active pipeline); `reject-log`
  diverts them to the optional `--reject-log` audit CSV instead.
- `--dry-run` — preview both would-be active rows and would-be lead rows;
  writes neither file.

`REVIEW` items become Lead Radar rows (classified `lead_type`, status
`reviewing`, a `HUMAN: confirm mattress/bedding scope before promotion.`
next-action) and are deduped against the existing Lead Radar, active, and
archive rows. Nothing flows from a lead into the active pipeline automatically:
a human must run `tools/lead_radar.py promote <lead-id> --confirmed-products
"..."` (see above), which is the only path across that boundary.

#### Outlook alert digest (email)

Portal alerts currently land in the Outlook business mailbox and are filed into
`Procurement Alerts`. The active no-admin operator route is a Microsoft Power
Automate digest from that folder to `beford@silverlinesleep.com`; the scheduled
Graph workflow is paused and manual-only. If Outlook forwarding to Gmail is
ever restored, `tools/ingest_email.py` can still recover the original portal
sender and subject from quoted `From:`/`Subject:` headers before relevance
routing. See `docs/email_ingest_setup.md` for the current operator setup.

### Review the operator dashboard

```sh
python tools/dashboard.py
python tools/dashboard.py --days 30
python tools/dashboard.py --show deadlines
python tools/dashboard.py --show drafts
```

The dashboard is read-only. It shows response deadlines, Q&A
deadlines, drafts ready to promote, missing owners or next actions,
stale reviews, scoring gaps, high-risk rows, and summary counts.

Flags worth knowing:

- `--days N` - deadline horizon, default `14`.
- `--stale-days N` - review age threshold, default `14`.
- `--show SECTION` - one of `all`, `deadlines`, `hygiene`, `risk`,
  `drafts`, or `summary`.

### Check workflow drift

```sh
python tools/workflow_check.py
python tools/workflow_check.py --fail-on-warnings
```

Hard errors include status mismatches, rows present in both active and
archive, closed rows left in active, active bid markdown without a
matching active pipeline row, and draft/submitted rows without active
markdown.

Warnings cover operator hygiene: missing owner, missing next action,
missing due date, stale `last_reviewed`, watching rows without
markdown, and no-bid archive rows without a memo.

### Ingest from SAM.gov

```sh
export SAM_API_KEY=...
python tools/ingest_sam.py \
    --title "mattress" \
    --posted-from 2026-05-01 \
    --posted-to 2026-05-14
```

Flags worth knowing:

- `--title TEXT` — substring match against opportunity title (the
  documented SAM.gov `title` parameter; SAM.gov has no general
  keyword/free-text search).
- `--naics-code CODE` — e.g. `337910` (mattress manufacturing); sent
  as `ncode`. The strongest single filter for cutting false positives.
- `--notice-type CODE` — single-letter procurement type code per
  SAM.gov docs: `o`=Solicitation, `k`=Combined Synopsis/Solicitation,
  `r`=Sources Sought, `p`=Pre-solicitation, `a`=Award, `s`=Special
  Notice; sent as `ptype`.
- `--response-deadline-after YYYY-MM-DD` — sent as `rdlfrom`. **Default
  is today**, so past-due opportunities are excluded automatically.
  Override with an earlier date to include some recent past-due, or
  pass `--include-past-due` to drop the filter entirely.
- `--response-deadline-before YYYY-MM-DD` — sent as `rdlto`. SAM.gov
  caps response-deadline ranges at 1 year.
- `--include-past-due` — opt out of the default `rdlfrom=today`
  filter. Useful for back-fill analysis; never use for live triage.
- `--limit N` — page size (SAM caps at 1000; default 50).
- `--max-pages N` — safety cap on pagination (default 10).
- `--api-key KEY` — overrides the `SAM_API_KEY` env var.
- `--active PATH` — pipeline CSV to append to.
- `--dry-run` — print what would be added; don't write.
- `--fixture PATH` — read a local JSON response (for tests / offline
  demos); skips the API call entirely.

The script never reads or writes `pointOfContact` fields from SAM.gov
responses — contact PII stays out of the repo by design.

### Ingest a portal CSV export

```sh
python tools/portal_csv_mapping.py path/to/portal-export.csv \
    --source "Portal Name"

python tools/ingest_portal_csv.py path/to/esbd-export.csv \
    --mapping configs/portal_csv/esbd.json \
    --dry-run

python tools/ingest_portal_csv.py path/to/esbd-export.csv \
    --mapping configs/portal_csv/esbd.json
```

Flags worth knowing:

- `--mapping PATH` — JSON mapping from portal CSV headers to canonical
  pipeline fields.
- `--source TEXT` — override the mapping's source label.
- `--<field>-column HEADER` — override one mapped CSV header from the
  command line, for example `--buyer-column "Agency Name"`.
- `--encoding TEXT` — decode exports that are not UTF-8, for example
  `--encoding cp1252`.
- `--allow-bad-dates` — proceed when mapped date values cannot be
  parsed; affected date fields are left blank and a warning is printed.

Bad dates fail the import by default because a blank due date can hide
a bid deadline.

### Create a portal CSV mapping

```sh
python tools/portal_csv_mapping.py path/to/portal-export.csv \
    --source "Beacon Bid"

python tools/portal_csv_mapping.py path/to/portal-export.csv \
    --source "Beacon Bid" \
    --write
```

The helper prints CSV headers, suggested canonical field mappings, and
unmapped headers. With `--write`, it creates
`configs/portal_csv/<source>.json` using the same shape consumed by
`tools/ingest_portal_csv.py`.

Review the generated config before importing. The suggestions are
conservative exact-header matches, not portal-specific certainty.

### Draft a bid response

```sh
python tools/draft_bid_response.py <opportunity-id> \
    --vendor vendor-profiles/<vendor>.profile.json \
    [--generated-date YYYY-MM-DD] [--force]
```

Flags worth knowing:

- `--active PATH` / `--archive PATH` — override the pipeline CSV
  locations searched for the opportunity.
- `--schema PATH` — override the profile-validation schema (defaults to
  `vendor-profiles/vendor_profile.schema.json`).
- `--output-dir DIR` — destination (default: `build/drafts/`).
- `--generated-date YYYY-MM-DD` — pin the timestamp for deterministic
  output.
- `--force` — overwrite an existing draft file.

The script validates the vendor profile against the schema before
drafting; a validation failure exits non-zero with the error list and
does not write a draft.

### Promote a draft into active bid work

```sh
python tools/promote_draft.py <opportunity-id>
```

The command verifies that the opportunity is still active, reads
`build/drafts/<opportunity-id>_draft.md`, and writes
`bids/active/<opportunity-id>.md`. It refuses to overwrite active
markdown or collide with archived markdown unless `--force` is passed.

Flags worth knowing:

- `--draft PATH` - promote an explicit draft path instead of the
  default `build/drafts/<opportunity-id>_draft.md`.
- `--output PATH` - write to an explicit destination path instead of
  `bids/active/<opportunity-id>.md`.
- `--force` - overwrite the destination markdown.

### Generate a packet

```sh
python tools/generate_procurement_packet.py \
    vendor-profiles/<vendor>_questionnaire.csv \
    --vendor "<Vendor Name>"
```

Flags:

- `--output-dir DIR` — destination (default: `build/generated/`).
- `--output-stem STEM` — filename stem (default: slug of vendor name).
  `--slug` is accepted as a backwards-compatible alias.
- `--generated-date YYYY-MM-DD` — pin the timestamp for deterministic
  output. Required when regenerating `generated/examples/`.
- `--answered-only` — drop rows whose Your Answer cell is blank.

### Validate a profile

```sh
python tools/validate_vendor_profile.py vendor-profiles/<vendor>.profile.json
```

Exit code is non-zero if any file fails.

### Run the test suite

```sh
python -m unittest discover -s tests
```

## Git hooks

| File | Purpose |
| --- | --- |
| `hooks/pre-push` | Refuses non-fast-forward pushes to `main`. Enable with `git config core.hooksPath tools/hooks`. |
