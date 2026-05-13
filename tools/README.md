# Tools

Lightweight Python utilities for the procurement toolkit.

## Procurement utilities

| Script | Stdlib only? | Purpose |
| --- | --- | --- |
| `generate_procurement_packet.py` | yes | Reads a questionnaire CSV, writes a markdown packet and printable HTML to `generated/`. |
| `validate_vendor_profile.py` | yes | Validates `vendor-profiles/*.json` against `vendor-profiles/schema/vendor_profile.schema.json`. Implements only the JSON Schema subset the schema actually uses, so no `jsonschema` dependency. |

### Generate a packet

```sh
python tools/generate_procurement_packet.py \
    vendor-profiles/<vendor>_questionnaire.csv \
    --vendor "<Vendor Name>" \
    --out-dir generated/
```

### Validate a profile

```sh
python tools/validate_vendor_profile.py vendor-profiles/<vendor>.json
```

Exit code is non-zero if any file fails.

## Git hooks

| File | Purpose |
| --- | --- |
| `hooks/pre-push` | Refuses non-fast-forward pushes to `main`. Enable with `git config core.hooksPath tools/hooks`. |

## Carried over from the DreamFinder split

The following scripts predate the procurement split and reference the
DreamFinder consumer app's onboarding folder layout. They are kept here
because the user explicitly asked not to break existing files, but they
are **not** part of the procurement workflow. Consider relocating them
to a `legacy/` folder or deleting them once you've confirmed nothing
external still depends on them.

| File | Original purpose |
| --- | --- |
| `convert_store_data.py` | DreamFinder retailer onboarding: spreadsheet → JS/CSS for the consumer app. |
| `create_template.py` | DreamFinder retailer onboarding: generates a blank `.xlsx` template. References `../onboarding/` paths that no longer exist in this repo. |
| `md_to_pdf.py` | DreamFinder onboarding: renders onboarding markdown to PDF. Also references missing `onboarding/*.md` paths. |
| `strip-bg.py` | Image utility for DreamFinder product photos. |
