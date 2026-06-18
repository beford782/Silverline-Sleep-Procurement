# Procurement source registry

`procurement_sources.json` is a machine-readable list of the portals,
cooperatives, and vendor databases where institutional mattress
opportunities surface. It is **data, not code** — later phases
(SAM.gov API ingestion, ESBD watchers, scoring) read from here so the
list of sources is editable without touching scripts.

## Shape

Top-level: a JSON array of source objects.

Each entry:

| Field | Type | Notes |
| --- | --- | --- |
| `name` | string | Display name. |
| `source_type` | enum | See below. |
| `official_url` | string | Empty string when the URL has not been verified inside this repo. |
| `has_api` | boolean | True only when a public documented API exists. |
| `requires_login` | boolean | True if reading or submitting requires authentication. |
| `intake_method` | enum | How opportunities reach us today. See below. |
| `geography` | array<string> | State codes, regions, or city names. |
| `buyer_level` | enum | See below. |
| `search_terms` | array<string> | Phrases to feed saved searches. |
| `commodity_terms` | array<string> | Categories the source uses to classify items. |
| `cadence` | enum | How often we expect to review this source. See below. |
| `notes` | string | Free-form context. Note URL-verification status here when `official_url` is empty. |

### Enumerated values

- `source_type`: `federal_portal | state_portal | city_portal | county_portal | isd_portal | university_portal | vendor_database | cooperative`
- `intake_method`: `api | saved_search | email_notification | manual_review | csv_export | portal_registration`
- `buyer_level`: `federal | state | county | city | isd | university | cooperative`
- `cadence`: `daily | weekly | monthly | ad_hoc`

## Adding or editing a source

1. Edit `procurement_sources.json` directly. Keep the file
   pretty-printed (2-space indent, sorted intuitively, UTF-8, LF).
2. Run `python -m json.tool sources/procurement_sources.json` to
   confirm it still parses.
3. Run `python -m unittest discover -s tests` — the registry tests
   enforce required fields and enum values.

## URL caution

Do **not** invent URLs. If the official URL has not been independently
confirmed (ideally cross-referenced against an in-repo doc like
`portal-checklists/continental_silverline_portal_setup.md`), leave
`official_url` empty and explain in `notes` that the URL is pending
verification. This rule exists because hallucinated URLs in operational
data are hard to spot once they're checked in.

## Contract research trackers

`txsmartbuy_contract_research.csv` stores contract-catalog intelligence
from operator-downloaded TxSmartBuy exports. These rows are useful for
NIGP code selection, saved-search setup, incumbent/category research, and
renewal monitoring. They are **not open solicitations** and should not be
imported into `bids/active/_pipeline.csv`.

## What this registry does NOT do

- It does not directly fetch opportunities. The first ingestion
  consumer is `tools/ingest_sam.py`, which currently reads the
  `intake_method: api` entry for SAM.gov. State/local portal
  ingestion is still future work.
- It does not enforce credentials, rate limits, or scrape sessions.
- It does not duplicate vendor commodity-code selections; those live
  in `portal-checklists/<vendor>_portal_setup.md`.
