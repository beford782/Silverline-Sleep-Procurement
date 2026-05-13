# Tools

Lightweight Python utilities for the procurement toolkit.

## Procurement utilities

| Script | Stdlib only? | Purpose |
| --- | --- | --- |
| `generate_procurement_packet.py` | yes | Reads a questionnaire CSV, writes a markdown packet and printable HTML. Default output dir is `build/generated/` (gitignored). |
| `validate_vendor_profile.py` | yes | Validates `vendor-profiles/*.profile.json` against `vendor-profiles/vendor_profile.schema.json`. Walks the schema at runtime; no parallel hardcoded rules. |

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

## Legacy

Pre-split DreamFinder helpers live under `tools/legacy/` and are not
part of the procurement toolkit. See `tools/legacy/README.md`.
