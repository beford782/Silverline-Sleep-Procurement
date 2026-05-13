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
  active/              Solicitations currently being pursued
  archive/             Closed / awarded / no-bid solicitations
  templates/           Reusable bid-response templates
portal-checklists/     Per-vendor portal-registration + commodity-code plans
templates/             Blank intake forms (questionnaires, etc.)
vendor-profiles/       Vendor profiles in markdown and structured JSON
  schema/              JSON Schema for the structured profile
generated/             Output of tools/ (markdown packets, HTML, etc.)
onboarding/            Internal onboarding notes for new vendors
procurement/           Domain overview and entry-point docs
tools/                 Python utilities (stdlib-only where possible)
  hooks/               Git hooks (e.g., pre-push fast-forward guard)
```

## Common workflows

### 1. Onboard a new vendor

1. Copy `templates/mattress_bid_setup_questionnaire.csv` and have the
   vendor fill in the **Your Answer** column.
2. Run the packet generator:
   ```sh
   python tools/generate_procurement_packet.py path/to/answers.csv \
       --vendor "Vendor Name" --out-dir generated/
   ```
3. Save the answered CSV under `vendor-profiles/<vendor>_questionnaire.csv`.
4. Author a structured `vendor-profiles/<vendor>.json` (see
   `vendor-profiles/continental_silverline.json` for shape).
5. Validate:
   ```sh
   python tools/validate_vendor_profile.py vendor-profiles/<vendor>.json
   ```
6. Capture the narrative profile in `vendor-profiles/<vendor>.md`.

### 2. Prepare a portal-registration plan

1. Read `portal-checklists/continental_silverline_portal_setup.md` as a
   reference.
2. Author `portal-checklists/<vendor>_portal_setup.md`, listing the
   portals to register on, commodity-code groups, saved searches, and
   the registration field tracker.

### 3. Stand up a bid response

1. Copy `bids/templates/bid_response_template.md` into
   `bids/active/<solicitation-id>.md`.
2. Fill in the solicitation, due dates, commodity codes, and assigned
   owner.
3. On award/decline, move the file to `bids/archive/`.

### 4. Track commodity codes

Commodity-code groups live alongside each vendor's
`portal-checklists/<vendor>_portal_setup.md`. Keep the canonical term
list there so all portals (CMBL, Bonfire, IonWave, Beacon Bid, etc.)
get the same vocabulary.

## Tools

Lightweight Python utilities, all stdlib-only where possible:

| Script | Purpose |
| --- | --- |
| `tools/generate_procurement_packet.py` | CSV questionnaire → markdown + printable HTML packet |
| `tools/validate_vendor_profile.py` | Validate `vendor-profiles/*.json` against the schema |

See `tools/README.md` for the full list (including legacy DreamFinder
helpers preserved during the split).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
