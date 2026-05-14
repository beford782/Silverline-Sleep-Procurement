# Tools

Lightweight Python utilities for the procurement toolkit.

## Procurement utilities

| Script | Stdlib only? | Purpose |
| --- | --- | --- |
| `pipeline.py` | yes | Manage the opportunity pipeline at `bids/active/_pipeline.csv`. Subcommands: `add`, `list`, `summary`, `score`, `move-to-archive`. Source registry at `sources/procurement_sources.json` documents where opportunities surface (SAM.gov / ESBD / Beacon Bid / Bonfire / cooperatives) — automated ingestion from those sources is **not yet implemented**. |
| `draft_bid_response.py` | yes | Render a starter bid response by combining one pipeline row (looked up by `opportunity_id` in active first, then archive) with a vendor profile JSON. Output is markdown under `build/drafts/` (gitignored) so generated content never collides with committed bid markdown. |
| `ingest_sam.py` | yes | Pull federal opportunities from SAM.gov's public API (`api.sam.gov/opportunities/v2/search`) into `bids/active/_pipeline.csv`. Stdlib HTTPS via `urllib.request`. Requires `SAM_API_KEY` env var. Dedupes by `solicitation_number` + `opportunity_id`. |
| `generate_procurement_packet.py` | yes | Reads a questionnaire CSV, writes a markdown packet and printable HTML. Default output dir is `build/generated/` (gitignored). |
| `validate_vendor_profile.py` | yes | Validates `vendor-profiles/*.profile.json` against `vendor-profiles/vendor_profile.schema.json`. Walks the schema at runtime; no parallel hardcoded rules. |

### Work the opportunity pipeline

```sh
python tools/pipeline.py add \
    --source "Texas ESBD" \
    --buyer "Texas Facilities Commission" \
    --solicitation-number "IFB 529-XYZ" \
    --title "Dormitory mattresses pilot" \
    --due-date 2026-06-15

python tools/pipeline.py list             # active rows, sorted by due_date
python tools/pipeline.py summary          # counts by status, source, risk
python tools/pipeline.py score --dry-run  # preview keyword-driven fit/risk
python tools/pipeline.py score            # write recomputed values
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

The scoring vocabularies live at the top of `tools/pipeline.py`
(`POSITIVE_KEYWORDS`, `CAUTION_KEYWORDS`, `STRONG_CAUTION`) and are
deliberately readable so they can be tuned to the institutional
mattress vocabulary you actually see in solicitations.

### Ingest from SAM.gov

```sh
export SAM_API_KEY=...
python tools/ingest_sam.py \
    --query "mattress" \
    --posted-from 2026-05-01 \
    --posted-to 2026-05-14
```

Flags worth knowing:

- `--query TEXT` — keyword passed as `?q=` to the API.
- `--naics-code CODE` — e.g. `337910` (mattress manufacturing).
- `--notice-type TEXT` — e.g. `Solicitation`,
  `"Combined Synopsis/Solicitation"`, `"Sources Sought"`.
- `--limit N` — page size (SAM caps at 1000; default 50).
- `--max-pages N` — safety cap on pagination (default 10).
- `--api-key KEY` — overrides the `SAM_API_KEY` env var.
- `--active PATH` — pipeline CSV to append to.
- `--dry-run` — print what would be added; don't write.
- `--fixture PATH` — read a local JSON response (for tests / offline
  demos); skips the API call entirely.

The script never reads or writes `pointOfContact` fields from SAM.gov
responses — contact PII stays out of the repo by design.

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
