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
2. Copy `bids/templates/bid_response_template.md` into
   `bids/active/<opportunity-id>.md` for the prose, open questions,
   and decision notes. Use the `opportunity_id` from the pipeline row
   as the filename.
3. On award/decline, archive both:
   ```sh
   python tools/pipeline.py move-to-archive <opportunity-id>
   git mv bids/active/<opportunity-id>.md bids/archive/<opportunity-id>.md
   ```

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

### 5. Future opportunity ingestion

`sources/procurement_sources.json` is the machine-readable list of
where opportunities surface (SAM.gov, Texas ESBD, Beacon Bid, Bonfire,
cooperatives, etc.). It's data, not code — later phases will read it
to drive automated ingestion. **SAM.gov / ESBD ingestion is not yet
implemented in this repo**; opportunities are added to the pipeline
manually via `tools/pipeline.py add`.

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
