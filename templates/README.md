# Templates

Blank intake forms and other reusable starting points.

## Current templates

| File | Purpose |
| --- | --- |
| `mattress_bid_setup_questionnaire.csv` | Vendor intake questionnaire. Used as the input to `tools/generate_procurement_packet.py`. |

## Adding a new template

Templates should be:

- Format-portable (CSV opens in Excel / Sheets / LibreOffice; markdown
  renders anywhere)
- Free of vendor-specific answers in the committed copy
- Documented in this README with one sentence on intended use

If a template is consumed by a script in `tools/`, name the script and
the option it expects (e.g., "feed to
`tools/generate_procurement_packet.py`").
