# Co-op / CMBL / University Coverage Plan - surfacing opportunities from no-auto-alert sources

- **For:** Blake / Continental Silverline Products, L.P.
- **Date:** 2026-06-27
- **Method:** Multi-agent research (10 source agents + synthesis) into how to capture opportunities
 from the registered sources that don't send per-opportunity alerts out of the box.

> **Key reframe:** these are NOT "no-alert by design." They are opt-in email-alert portals
> (IonWave / Jaggaer / OpenGov / eSystems) where we either never registered or never selected the
> furniture / FF&E / mattress-bedding / dormitory commodity codes. Register with the right codes and
> the **pipeline inbox** as contact, and their per-opportunity emails flow straight into the
> email-ingest pipeline we just built (`daily_email_ingest.yml`). The ingestion is done; the gap is
> the one-time registrations + a re-bid calendar.

---

## Bottom line

For all nine sources the fix is the same in spirit: these are not "no-alert" portals, they are **opt-in email-alert portals where we either never registered or never selected the furniture / FF&E / mattress-bedding / dormitory commodity codes.** The single highest-leverage move is to register (or repair the registration) in each portal using **one shared pipeline-monitored inbox** as the contact email and check the relevant commodity codes, so per-opportunity emails flow into the pipeline automatically " no scraping, fully compliant. The 2-3 most time-sensitive actions: (1) **finish the HCDE/Choice Partners eBid registration now** " it was the one blocked on the SAM.gov UEI, which is now assigned; (2) **fix the Texas CMBL profile** (point its notification email at the pipeline inbox and add NIGP classes 030/205 bedding, 420/425 furniture) because CMBL is the master alert channel that also covers UT-Houston and most TX agencies; (3) **register in TIPS, BuyBoard, Sourcewell, OMNIA, AggieBid, and UTSSCA-Jaggaer** so the next furniture re-bid (several land in the 2027-2029 window) is not missed. Note: **no furniture/mattress/FF&E solicitation is open at any of these sources right now** " every relevant master contract is mid-term, so this is about wiring the alerts before the next re-bid, not chasing a live bid today.

## Per-source plan

| Source | Recommended mechanism | One-time setup action | Confidence |
|---|---|---|---|
| TIPS (Region 8 ESC) | Official supplier bid-alert email (IonWave/Euna) | Register at https://tips.ionwave.net/ (via https://www.tips-usa.com/becomebidder.cfm); select Furniture/Furnishings & household-goods codes; contact = pipeline inbox | High |
| Choice Partners / HCDE | Official per-opportunity email (HCDE eBid / IonWave) | **Finish the paused registration** at https://hcdeebid.ionwave.net/VendorRegistration.aspx; select FF&E + mattress/bedding + dormitory + household-goods codes; email purchasing@hcde-texas.org to confirm 23/022MF expiry | High |
| Sourcewell | Official supplier portal email alerts | Create account at https://proportal.sourcewell-mn.gov/ ; select furniture/FF&E codes | High |
| OMNIA Partners | Official "Solicitation Mailing List" + e-bid account | Submit form at https://www.omniapartners.com/get-started/solicitations ; select furniture/FF&E/mattress/dormitory/household-goods | Medium |
| BuyBoard (TASB) | Official per-commodity email (IonWave) | Register/repair at https://buyboard.ionwave.net/Login.aspx ; select Furniture (School/Office/Library/Dormitory) + any Bedding category | High |
| HGACBuy | Official OpenGov portal Subscribe/Follow | Sign up at https://procurement.opengov.com/portal/h-gac ; Subscribe to furniture/FF&E/furnishings/household-goods (note: category may be thin/absent " add quarterly manual check) | Medium |
| Texas CMBL | **The master TX email-alert channel** (NIGP-code driven) | In eSystems (https://comptroller.texas.gov/purchasing/vendor/cmbl/): set notification email to pipeline inbox; add NIGP Class 030 (bedding/linens), 420 & 425 (furniture/dormitory); keep $70/yr active | High |
| UT System (UTSSCA / campuses) | Jaggaer supplier alerts + ESBD + Bonfire | Register at https://solutions.sciquest.com/apps/Router/RegistrationChecklist?CustOrg=MDAndersonPS (NIGP 420 + beds/mattress); mirror on Texas SmartBuy/ESBD and UT Austin Bonfire | Medium |
| Texas A&M (AggieBid) | Jaggaer per-commodity email alerts | Register at https://solutions.sciquest.com/apps/Router/SupplierLogin?CustOrg=TAMU ; add furniture/mattress/bedding/FF&E/household codes; help: vendorhelp@tamu.edu | High |
| University of Houston | **Already covered by Texas CMBL** (UH posts to ESBD) | No new portal " verify CMBL NIGP codes 205/420/425 are selected (see CMBL row); optional Google Alert backup | High |

## Upcoming opportunity calendar

**Plainly: nothing in our category (mattress / bedding / FF&E / dormitory / furniture) is currently open at any of these nine sources as of 2026-06-27.** Every relevant master contract is mid-term. What exists is a set of **re-bid windows** to watch (none of these dates are officially published yet " treat as estimates, do not commit to bids on them):

| Title / contract | Source | Re-bid / close window (estimated unless noted) | Link |
|---|---|---|---|
| Dorm/Residence-Hall Furniture (Region 4 ESC master) | OMNIA Partners | Expires ~09/30/2029 (renewal to ~10/31/2031) ' re-bid ~2028-2029 | https://www.omniapartners.com/publicsector/contracts/furniture |
| Furniture Solutions w/ Related Accessories (RFP #091423) | Sourcewell | Expires **2027-12-04** ' replacement RFP expected ~mid-2027 | https://www.sourcewell-mn.gov/solicitations/10745 |
| Furniture for School/Office/Library/Dormitory (Proposal 767-25) | BuyBoard | Contract 04/01/2025 "**03/31/2028** ' re-bid ~late 2027/early 2028 | https://www.buyboard.com/vendor/proposal-invitations |
| Furniture, Furnishings & Services (TIPS #230301) | TIPS | Renewals through **05/31/2028** ' re-bid expected ~late 2027/early 2028 | https://www.withpavilion.com/solicitations/0db76ebc-6577-4fc0-8cc3-3019cba194ab |
| FF&E and Related Items (contract 23/022MF) | Choice Partners/HCDE | Expiry not published ' confirm via purchasing@hcde-texas.org; est. re-bid ~2027-2028 | https://www.choicepartners.org/current-rfps |
| Mattresses, Related Products & Services (UC lead-agency master) | OMNIA Partners | Expires ~08/31/2031 ' re-bid ~2030-2031 | https://www.omniapartners.com/get-started/solicitations |

UT System, Texas A&M (AggieBid), Texas CMBL, and University of Houston issue furniture/bedding solicitations **ad hoc** (no fixed cycle) " there is no calendar date to set; the commodity-code email alert is what catches each one when it posts.

## What I can wire into the pipeline

The pipeline's `configs/feeds.json` ingests **RSS/Atom feeds** (each entry is `{ "source", "url" }`). It already pulls Bonfire RSS feeds (Harris County, UT Austin, UT Health SA, TDCJ, etc.).

**Truly automatable (RSS) " safe repo changes:**

- **HGACBuy (OpenGov):** OpenGov portals expose opportunity feeds, but the relevant value is low (furniture/FF&E category appears thin/absent). The reliable automatable path is a **Google Alert delivered as RSS**. Add to `configs/feeds.json`:
 ```json
 { "source": "Google Alert: HGACBuy FF&E", "url": "<RSS-feed-URL-from-google.com/alerts for: site:hgacbuy.org (furniture OR mattress OR bedding OR FF&E)>" }
 ```
- **Texas CMBL / ESBD / University of Houston:** add a Google-Alert-as-RSS backstop for ESBD postings:
 ```json
 { "source": "Google Alert: TX ESBD bedding/furniture", "url": "<RSS-URL for: site:txsmartbuy.gov (mattress OR bedding OR \"dormitory furniture\")>" },
 { "source": "Google Alert: UH ESBD", "url": "<RSS-URL for: site:txsmartbuy.gov \"University of Houston\" (mattress OR bedding OR furniture OR dormitory)>" }
 ```
- **Choice Partners, TIPS:** Google-Alert-as-RSS on the public RFP pages (`site:choicepartners.org` and `site:tips-usa.com furniture OR mattress`) as belt-and-suspenders, same pattern.

Concrete repo change for all of the above: create each alert at google.com/alerts ' set "Deliver to: RSS feed" ' copy the generated feed URL ' append the object(s) to `configs/feeds.json` (mirroring the existing Bonfire entries). These are the only compliant feeds available, since none of these portals publish a native bid RSS.

**NOT automatable " require a human one-time registration + (for re-bids) a calendar reminder:**

- TIPS, Choice Partners/HCDE, Sourcewell, OMNIA, BuyBoard, AggieBid, UTSSCA-Jaggaer, Texas CMBL " these run on **IonWave / Jaggaer / OpenGov / eSystems** with **no public bid RSS**. Their alerts are email-only and only fire after a human completes registration and selects commodity codes. Once registered with the **shared pipeline inbox** as the contact, the per-opportunity emails become an ingestable stream (if the pipeline has an email-intake path) " but the registration itself is a manual action, not a config change.
- Re-bid windows (Sourcewell ~mid-2027, BuyBoard/TIPS ~late-2027/early-2028, OMNIA dorm ~2028-2029 and mattress ~2030-2031) need **human calendar reminders** " set them ~4-6 months ahead of each expiry.

## Honest gaps

- **No native bid RSS exists for any of these sources.** Every recommended "automated" feed is a **Google Alert delivered as RSS** over a public page, which is a best-effort backstop, not a guarantee " Google may miss or delay postings, and several portals (tips-usa.com, OMNIA solicitations, HGAC OpenGov index) return **HTTP 403 to automated fetches**, so even passive checking of them is blocked. The authoritative channel for all of these remains the **opt-in commodity-coded email**, which depends on a human completing registration correctly.
- **HGACBuy** may have **no furniture/mattress/FF&E contract category at all** (its catalog skews to vehicles, heavy equipment, infrastructure). If so, there is no mechanism to wire because there is nothing relevant to surface " a quarterly manual check of https://www.hgacbuy.org/bid-notices is the honest fallback.
- **Re-bid dates are estimates, not confirmed.** Exact next-solicitation open dates for TIPS #230301, BuyBoard 767-25, Sourcewell #091423, Choice Partners 23/022MF, and the OMNIA masters are **not publicly published**. The 2027-2031 windows are derived from contract-expiry math and must be confirmed with each co-op (e.g., purchasing@hcde-texas.org for HCDE, UTSSCAINFO@mdanderson.org for UT) before relying on them.
- **Email-intake dependency:** converting the email alerts into pipeline visibility assumes the pipeline can ingest a monitored inbox. If it currently only ingests RSS + SAM.gov API, the email-alert sources will land in an inbox a human still has to watch until an email-intake path is built.

Relevant repo file for the automatable changes: `C:\Users\BlakeFord\Documents\GitHub\Silverline-Sleep-Procurement\configs\feeds.json`

### Scope note
Docs only. URLs/dates are agent-researched estimates - confirm re-bid dates with each co-op before relying on them.
