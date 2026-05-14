# {{Solicitation Title}} — No-Bid Memo

| Field | Value |
| --- | --- |
| Solicitation # | {{IFB / RFP / RFQ number}} |
| Buyer | {{Agency / Jurisdiction}} |
| Decision date | YYYY-MM-DD |
| Vendor | [{{vendor name}}](../../vendor-profiles/{{vendor}}.md) |
| Decision owner | {{name}} |
| Portal | {{ESBD / Beacon Bid / Bonfire / IonWave / SAM.gov / cooperative}} |
| Opportunity id | {{matches `bids/active/_pipeline.csv` row}} |

## 1. Summary

One paragraph describing what the buyer was asking for: product
categories, sizes, quantities, delivery scope, contract type, term
length. Anything that materially shaped the bid/no-bid call.

## 2. Disqualifying factor(s)

- **Primary reason:** _the single biggest factor — pricing risk,
  delivery scope outside service geography, missing certification,
  MOQ too small, payment terms, etc._
- **Contributing reasons:** _other factors that, alone, would have
  been workable._

Cross-reference the vendor profile's no-bid conditions
(`contract_preferences.no_bid_conditions`) if the disqualifier is
already documented there.

## 3. What would change a future bid/no-bid call

Concrete vendor or market changes that would flip this decision:

- _e.g., adding inside delivery via a Texas subcontractor_
- _e.g., raising insurance umbrella limit to $5M_
- _e.g., completing SAM.gov registration_
- _e.g., obtaining HUB certification_

## 4. Lessons captured

- _e.g., add this buyer's standard delivery requirements to the vendor
  profile's `setup_gaps` list_
- _e.g., add `liquidated damages` to the pipeline scoring caution
  vocabulary_
- _e.g., add this commodity code group to
  `portal-checklists/<vendor>_portal_setup.md`_

## 5. Pipeline housekeeping (operator checklist)

- [ ] Set `bids/active/_pipeline.csv` row `status` to `no-bid`
- [ ] Move the pipeline row to archive: `python tools/pipeline.py
      move-to-archive <opportunity-id>`
- [ ] If a draft markdown exists at `bids/active/<id>.md`, `git mv`
      it to `bids/archive/<id>.md`
- [ ] Optionally save this memo as
      `bids/archive/<id>_no_bid.md` for future reference
