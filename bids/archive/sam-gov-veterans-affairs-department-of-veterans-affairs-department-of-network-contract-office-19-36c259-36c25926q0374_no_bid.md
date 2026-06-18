# Beds and Mattresses for Pueblo VA CLC - No-Bid Memo

| Field | Value |
| --- | --- |
| Solicitation # | 36C25926Q0374 |
| Buyer | VA Eastern Colorado Healthcare System / Rocky Mountain Regional VAMC - Network Contract Office 19 (36C259) |
| Decision date | 2026-06-18 |
| Vendor | [Continental Silverline](../../vendor-profiles/continental_silverline.md) |
| Decision owner | Operator |
| Portal | SAM.gov |
| Notice type | Combined Synopsis/Solicitation (RFQ), firm-fixed-price, unrestricted |
| Response due | 2026-07-02 (questions 2026-06-23) |
| Opportunity id | sam-gov-veterans-affairs-department-of-veterans-affairs-department-of-network-contract-office-19-36c259-36c25926q0374 |

## 1. Summary

RFQ for the Pueblo VA Community Living Center, delivered to the Rocky
Mountain Regional VAMC in Aurora, CO (NAICS 337910 / PSC 7210), quotes due
2026-07-02. The title "Beds and Mattresses" and the mattress NAICS/PSC
codes produced an inflated keyword fit_score (55), but the statement of
work shows the deliverable is **powered medical beds**, not institutional
bedding. No-bid.

## 2. Disqualifying factors

The requirement fails on three independent grounds:

- **Primary reason - product mismatch.** The line items are 2 low-profile
  bariatric beds and 25 hospital beds. The salient characteristics describe
  electric/powered medical equipment: >=800 lb capacity with integrated
  scale, low height (<=12"), powered repositioning, bed-exit alarm, digital
  status display, CPR electronic + manual controls, Aux 110V/USB outlets,
  patient call button, and >=500 lb trapeze bars. The mattresses are bundled
  accessories to the beds. Continental manufactures mattresses, bed frames,
  and box springs (Restonic / Spring Air / Silverline Sleep) - **not powered
  hospital or bariatric beds.**
- **Geography.** Place of performance is Aurora, CO, outside Continental's
  TX / OK / LA / MS / AR / NM own-fleet, dock-delivery service geography.
- **Bundled services.** Line items also require onsite delivery and
  installation, removal/disposal of existing equipment (vendor:
  `mattress_removal_disposal: no`), and onsite training - all in Colorado.

## 3. What would change a future bid/no-bid call

- A VA or other public-sector solicitation for **institutional mattresses,
  frames, or box springs** (the actual product line) inside the
  Gulf/South-Central delivery region.
- None of the above changes here are partial - product, geography, and
  services each independently disqualify this notice.

## 4. Lessons captured

- A "beds and mattresses" title with a matching mattress NAICS (337910) /
  PSC (7210) is **not** sufficient evidence of product fit. Read the line
  items and salient characteristics: VA "beds" notices are frequently for
  powered hospital/bariatric beds (medical equipment), which the
  title-and-code relevance filter cannot distinguish from bedding.
- Treat the ingest fit_score as a triage prompt, not a fit conclusion, when
  the buyer is a hospital/clinical facility (VAMC, CLC).
