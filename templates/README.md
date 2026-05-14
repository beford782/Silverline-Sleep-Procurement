# Templates

Blank intake forms and other reusable starting points.

## Current templates

| File | Purpose |
| --- | --- |
| `mattress_bid_setup_questionnaire.csv` | Vendor intake questionnaire. Used as the input to `tools/generate_procurement_packet.py`. |
| `opportunity_tracker.csv` | Blank header for the live opportunity pipeline. `bids/active/_pipeline.csv` and `bids/archive/_pipeline_archive.csv` share this header; managed via `tools/pipeline.py`. |
| `bid_package_checklist.md` | Reusable shell for what goes into a bid response: cover materials, vendor info, product docs, pricing, references, insurance, certifications, submission. Operator copies and ticks off per bid. |
| `no_bid_memo_template.md` | Short structured memo for documenting why a solicitation was declined. Pairs with `tools/pipeline.py move-to-archive`. Filename convention when kept: `bids/archive/<opportunity-id>_no_bid.md`. |
| `trackers/portal_registration_tracker.csv` | Per-vendor portal-registration tracker (CMBL, Bonfire, IonWave, Beacon Bid, cooperatives, etc.). Header-only template. |
| `trackers/commodity_code_tracker.csv` | Per-vendor commodity-code subscriptions across portals. Header-only template. |

### Tracker enums

`portal_registration_tracker.csv` columns:

- `status`: `not_registered | in_progress | registered | expired`
- Date columns (`registration_date`, `renewal_date`, `last_reviewed`):
  `YYYY-MM-DD`
- `commodity_codes` and `documents_uploaded`: semi-separated within
  the cell (e.g., `055-58; 410-95`)

`commodity_code_tracker.csv` columns:

- `code_system` (free text; common values: `NIGP`, `UNSPSC`, `CMBL`,
  `Bonfire`, `IonWave`, `BeaconBid`, `Cooperative-specific`)
- `vendor_subscribed`: `yes | no | pending`
- `relevance`: `low | medium | high`
- `portals`: semi-separated list of portal names

### Future automation note

No script reads `trackers/*.csv` yet. A future PR may add a
`tools/portal_status.py` that cross-references these trackers with
`sources/procurement_sources.json` and reports gaps. Until then, the
files are operator-only working trackers.

## Adding a new template

Templates should be:

- Format-portable (CSV opens in Excel / Sheets / LibreOffice; markdown
  renders anywhere)
- Free of vendor-specific answers in the committed copy
- Documented in this README with one sentence on intended use

If a template is consumed by a script in `tools/`, name the script and
the option it expects (e.g., "feed to
`tools/generate_procurement_packet.py`").
