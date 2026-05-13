# Vendor Profiles

Each vendor has up to three files in this folder:

| File | Purpose |
| --- | --- |
| `<vendor>.md` | Narrative public-sector pursuit profile. Human-reviewed. |
| `<vendor>.json` | Structured profile, validated against `schema/vendor_profile.schema.json`. |
| `<vendor>_questionnaire.csv` | The filled-in intake questionnaire that produced the packet. |

The structured JSON is the canonical machine-readable record. The
markdown narrative is the human-reviewed companion. The CSV is the
provenance trail showing where the profile came from.

## Schema

`schema/vendor_profile.schema.json` is JSON Schema 2020-12 with a
deliberately narrow surface (type, required, enum, additionalProperties,
items, properties, minLength, minimum). The
`tools/validate_vendor_profile.py` script implements exactly that
subset, so no external dependency is needed.

Top-level sections:

- `vendor` — legal name, DBA, primary location, last-updated date
- `company` — manufacturing location, service geography, delivery
- `products` — product fit map (`yes` / `no` / `tbd` per product slug)
- `compliance` — spec sheets, fire safety, sizes, insurance
- `reference_contracts` — past awards usable as references
- `target_buyers` — `highest` priority vs. `develop`
- `contract_preferences` — fixed-price comfort, volume, types
- `portal_status` — list of `{portal, status, next_step}`
- `setup_gaps` — outstanding items to close before pursuing certain
  bids

## Adding a new vendor

1. Drop the filled questionnaire CSV in here as
   `<vendor>_questionnaire.csv`.
2. Run the packet generator to produce starter markdown:
   ```sh
   python tools/generate_procurement_packet.py \
       vendor-profiles/<vendor>_questionnaire.csv \
       --vendor "<Vendor Name>" --out-dir generated/
   ```
3. Curate the markdown into `<vendor>.md` (the generated packet is a
   starting point; the committed narrative should be tighter and
   strip contact info).
4. Hand-author `<vendor>.json` against the schema.
5. Validate:
   ```sh
   python tools/validate_vendor_profile.py vendor-profiles/<vendor>.json
   ```

## Privacy

These files are public-sector pursuit documents. Names, emails, phone
numbers, and street addresses should not be committed. Use `private`
as the value where a contact field is required.
