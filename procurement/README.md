# Procurement Overview

This folder is an index, not a content folder — the procurement
materials it originally held have moved to dedicated top-level folders.

## Where everything went

| Old location | New location |
| --- | --- |
| `procurement/continental_silverline_bid_setup_profile.md` | `vendor-profiles/continental_silverline.md` |
| `procurement/step_2_portal_and_commodity_checklist.md` | `portal-checklists/continental_silverline_portal_setup.md` |
| `procurement/mattress_bid_setup_questionnaire.csv` | `templates/mattress_bid_setup_questionnaire.csv` |

The split lets us add more vendors without piling unrelated documents
on top of each other.

## Procurement-domain glossary

A short, opinionated dictionary of the terms used across this repo.

- **Solicitation** — the umbrella term for any public-sector buying
  document (IFB, RFP, RFQ, sources sought, etc.).
- **IFB / Invitation for Bid** — sealed bid for a defined scope, lowest
  responsive bidder wins.
- **RFP / Request for Proposal** — scored response with technical and
  pricing components.
- **RFQ / Request for Quote** — short-form pricing request, often below
  a formal-bid threshold.
- **NIGP code** — National Institute of Governmental Purchasing
  commodity code. State and local portals use these to route
  notifications.
- **Cooperative** — purchasing vehicle (BuyBoard, TIPS, HGACBuy,
  Sourcewell, OMNIA, Choice Partners) that lets agencies buy off an
  already-awarded contract.
- **Commodity code** — generic term covering NIGP and portal-specific
  category codes.
- **Saved search** — a recurring query on an opportunity board (ESBD,
  Beacon Bid, Bonfire) used to surface new postings without manual
  hunting.
- **No-bid conditions** — the bright-line requirements that
  automatically disqualify a solicitation from pursuit (e.g., MOQ,
  delivery scope, insurance limits, payment terms).
- **Opportunity pipeline** — the running CSV of opportunities at
  `bids/active/_pipeline.csv` (closed rows move to
  `bids/archive/_pipeline_archive.csv`). Managed via
  `tools/pipeline.py`. Each opportunity has a stable `opportunity_id`
  that doubles as the filename for any matching narrative markdown
  under `bids/active/`.
- **Source registry** — `sources/procurement_sources.json`, a
  machine-readable list of opportunity portals (SAM.gov, ESBD, Beacon
  Bid, Bonfire, cooperatives, etc.) plus the search vocabularies and
  intake methods we use against each. Currently data-only; a future
  phase will read it to drive automated intake.
- **Fit score / risk level** — keyword-driven scoring applied by
  `tools/pipeline.py score`. Positive keywords (mattress, dormitory,
  correctional, cot, shelter, …) add to the score; caution keywords
  (anti-ligature, removal, installation, nationwide, multi-year, …)
  subtract. Strong-caution terms (`anti-ligature`, `liquidated
  damages`, `nationwide`) force `risk_level=high` regardless. Score
  thresholds: `<40` high, `40–69` medium, `≥70` low.

## Operational workflow at a glance

1. **Intake** — `tools/pipeline.py add …` to register a new
   opportunity. SAM.gov / ESBD ingestion is not yet automated; rows
   are added manually for now.
2. **Triage** — `tools/pipeline.py score` to compute fit and risk
   bands deterministically from the title + commodity terms + notes.
3. **Decide** — author per-solicitation prose in
   `bids/active/<opportunity-id>.md` from the bid response template.
4. **Close** — `tools/pipeline.py move-to-archive <opportunity-id>`
   and `git mv` the markdown into `bids/archive/`.

## Companion docs

- Top-level workflows: [`../README.md`](../README.md)
- Onboarding playbook: [`../onboarding/README.md`](../onboarding/README.md)
- Vendor profiles: [`../vendor-profiles/README.md`](../vendor-profiles/README.md)
- Portal checklists: [`../portal-checklists/README.md`](../portal-checklists/README.md)
- Bid tracking and pipeline: [`../bids/README.md`](../bids/README.md)
- Source registry: [`../sources/README.md`](../sources/README.md)
