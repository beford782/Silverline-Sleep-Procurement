# Residential Housing Mattresses - Haskell Indian Nations University (140A2326Q0283) - No-Bid Memo

| Field | Value |
| --- | --- |
| Solicitation # | 140A2326Q0283 |
| Buyer | Dept of the Interior - Bureau of Indian Education, Indian Education Acquisition Office (Albuquerque NM) for Haskell Indian Nations University, Lawrence KS |
| Decision date | 2026-08-31 |
| Vendor | [Continental Silverline](../../vendor-profiles/continental_silverline.md) |
| Decision owner | Blake |
| Portal | SAM.gov (email-back RFQ; POC Jeff Morris, jeff.morris@bie.edu, 505-364-2130) |
| Opportunity id | sam-gov-interior-department-of-the-bureau-of-indian-affairs-indian-education-acquisition-office-140a2326q0283 |

## 1. Summary

Combined Synopsis/Solicitation posted 2026-08-25, due 2026-09-08 14:00 CT,
NAICS 337910 / PSC 7210, LPTA, single firm-fixed-price PO, period of
performance from 2026-10-01 (~30 days). Surfaced by the 2026-08-27 SAM ingest
(PR #163) at fit 95 - and the fit score is right: the SOW is 220 twin
38"x75"x9" 10 oz navy vinyl mattresses to 16 CFR 1633, "American Bedding
catalog equal to or greater", plus 8 XL, with delivery, installation and
removal/disposal across four residence halls (Osceola-Keokuk, Blalock, Roe
Cloud, Winona). Squarely a CSP product at a real quantity.

## 2. Disqualifying factors

- **Primary reason:** Buy Indian Act. The SF-1449 schedule states
  "THIS ACTION IS SET-ASIDE 100% FOR INDIAN SMALL BUSINESS ECONOMIC
  ENTERPRISES (ISBEEs)"; the package carries an IEE Representation Form
  (Attachment 3) and DIAR 1452.280 clauses, and SAM codes the set-aside as
  `ISBEE`. Continental Silverline is not an Indian Economic Enterprise, so
  it is ineligible to prime regardless of price or product fit.
- **Contributing reasons:** None needed - eligibility alone decides it.
  Delivery to Lawrence KS and a 4-building install would otherwise have
  been workable.

## 3. What would change a future bid/no-bid call

- An ISBEE dealer/distributor primes the buy and sources CSP mattresses.
  CSP is a small manufacturer, so an IEE nonmanufacturer can offer its
  product under the nonmanufacturer rule, and the DIAR limitation-on-
  subcontracting clause governs the prime's labor share, not the mattress
  source. This is the only route into BIA/BIE/IHS mattress demand.
- A BIA/BIE/IHS notice issued without a Buy Indian set-aside (a deviation
  or a re-solicitation after no IEE offers) - rare, but it is why these
  rows are still worth a 30-second set-aside check rather than a blanket
  filter.

## 4. Lessons captured

- The relevance gate scores NAICS/PSC/keywords and never reads the
  set-aside code, so BIA/BIE/IHS mattress buys will keep landing in the
  active pipeline at fit 95. Check `solicitation.setAside` on every
  Interior/IHS row on arrival; `ISBEE` or `IEE` means archive no-bid the
  same day. (The same blind spot covers 8(a), SDVOSB, WOSB and HUBZone
  set-asides CSP cannot claim - a set-aside eligibility gate in ingest is
  the follow-up fix.)
- If a third Buy Indian mattress notice appears, build the IEE-dealer
  partner list rather than triaging each one from scratch: the spec
  pattern (vinyl institutional twin, 16 CFR 1633, install/removal) is
  identical across BIE residential halls.
