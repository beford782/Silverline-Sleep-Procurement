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
  legacy/                Pre-split DreamFinder helpers — not procurement tooling
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
3. When the draft is in shape, copy it into
   `bids/active/<opportunity-id>.md` and edit the prose, open
   questions, and final decision by hand. The draft is regenerable;
   the committed markdown is the operator's source of truth.
4. On award/decline, archive both:
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
python tools/pipeline.py summary          # counts by status, source, risk
python tools/pipeline.py score --dry-run  # preview keyword-driven fit/risk
python tools/pipeline.py score            # write the recomputed values
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
    --query "mattress" \
    --posted-from 2026-05-01 \
    --posted-to 2026-05-14 \
    [--naics-code 337910] \
    [--notice-type "Solicitation"] \
    [--dry-run]
```

Behavior:

- Fetches all matching opportunities (paginated, capped by
  `--max-pages`).
- Maps documented SAM.gov fields onto the pipeline schema; never
  pulls contact PII.
- Dedupes against `bids/active/_pipeline.csv` by both
  `opportunity_id` and `solicitation_number`, so re-running with an
  overlapping date range is safe.
- `--dry-run` previews what would be added without writing.

`sources/procurement_sources.json` is the machine-readable list of
where opportunities surface. State/local portal ingestion (ESBD,
Beacon Bid, Bonfire, IonWave, cooperatives) is **not yet implemented**
— rely on portal-side email notifications and add those rows
manually via `tools/pipeline.py add` for now.

### 6. Track commodity codes

Commodity-code groups live alongside each vendor's
`portal-checklists/<vendor>_portal_setup.md`. Keep the canonical term
list there so all portals (CMBL, Bonfire, IonWave, Beacon Bid, etc.)
get the same vocabulary.

## Tools

Lightweight Python utilities, all stdlib-only where possible:

| Script | Purpose |
| --- | --- |
| `tools/pipeline.py` | Manage `bids/active/_pipeline.csv`: add, list, summary, score, move-to-archive |
| `tools/draft_bid_response.py` | Combine an opportunity row with a vendor profile to render a starter response markdown under `build/drafts/` |
| `tools/ingest_sam.py` | Pull federal opportunities from the SAM.gov public API (stdlib `urllib`) into the pipeline. Requires `SAM_API_KEY`. |
| `tools/generate_procurement_packet.py` | CSV questionnaire → markdown + printable HTML packet |
| `tools/validate_vendor_profile.py` | Validate `vendor-profiles/*.profile.json` against the schema |

Run the test suite with:

```sh
python -m unittest discover -s tests
```

See `tools/README.md` for the full tool inventory and
`tools/legacy/README.md` for the pre-split DreamFinder helpers.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
