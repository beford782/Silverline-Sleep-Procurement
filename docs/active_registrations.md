# Active Registrations Ledger — Continental Silverline Products, LLC

- **For:** Blake / Continental Silverline Products, LLC (Houston, TX)
- **Last updated:** 2026-07-17
- **Purpose:** Single source of truth for **where we are registered to bid**, so any new pursuit can pull the right portal, login, and commodity setup at a glance. Consolidates registration status previously scattered across `leads/review/_lead_radar.csv` notes and `vendor-profiles/`.

> **Notification mailbox:** all portals point to the business mailbox **beford@silverlinesleep.com**, which forwards into the ingest funnel (Power Automate → `ingest_email.py` → `relevance.py` → pipeline/Lead Radar). See [`email_ingest_setup.md`](email_ingest_setup.md).
>
> **PII rule:** vendor account numbers shown below are non-secret portal IDs (not passwords). The **CMBL number, EIN, phone, and street address are kept OUT of version control** — they live in the operator's records / local memory, shown here as `[on file]`.

**Status legend:** ✅ active/confirmed · 🟡 in progress · ⬜ target (not yet registered) · ⛔ skip (no fit)

---

## Federal

| Buyer / vehicle | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **SAM.gov** (all federal contracts) | SAM.gov | ✅ **ACTIVE (2026-07-17)** | UEI **XF73FG8CVMX1**, record name **Continental Silverline Products, LLC** (corrected); CAGE **[record code here — from the SAM activation notice]** | NAICS 337910 (primary, Small Business Y); PSC 7210/7105 (US-made); Disaster Response Registry opted in | **2026-07-17: registration ACTIVE — UEI is now citable on federal bids.** History: 2026-07-07 registration SUBMITTED under the corrected LLC name. GSA approved the L.P.→LLC entity-validation correction (INC-GSAFSD21285074) the same morning; operator re-validated, all sections completed (incl. taxpayer + banking, operator-entered), submitted. IRS TIN match passed; **2026-07-09: DLA CAGE review letter received AND answered same day** — response sent in-thread with Formation cert + Merger cert + same-day Comptroller ACTIVE-status screenshot (details in [`drafts/dla_cage_response_XF73FG8CVMX1_2026-07-09.md`](drafts/dla_cage_response_XF73FG8CVMX1_2026-07-09.md); explained legacy CAGE 19865 = same business pre-merger, no open federal contracts under prior names). Then CAGE assignment → **Active**. Do **NOT** cite the UEI on bids until status = Active. |

## Texas — state & home market

| Buyer / vehicle | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **Texas CMBL** | Comptroller CMBL | ✅ active | `[on file]` | NIGP 205/420 (+correctional/medical/dorm) | Drives TX state-agency notifications |
| **Texas ESBD / SmartBuy** | ESBD | ✅ active | — | saved searches (mattress/bedding/dorm/correctional) | Highest-leverage TX state board (TDCJ, TJJD, HHSC, TDEM) |
| **City of Houston** | Beacon Bid | ✅ active | — | commodity notifications | Home-city procurement |

## Cooperative contract vehicles

| Co-op | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **TIPS** (Region 8 ESC) | IonWave | ✅ complete (2026-06-19) | — | mattress, bedding, dorm/institutional furniture, FF&E | Furniture re-bid ~yearly = shortest path to bid |
| **EPIC6 / Region 6 ESC** | IonWave | ✅ confirmed (2026-06-19) | — | furniture, dorm, mattresses, bedding, shelter/correctional | Alert keywords verified |
| **Region 4 ESC / OMNIA** | IonWave | ✅ confirmed (2026-06-22) | — | mattress, bedding, beds, bed frame, dorm | Gateway to OMNIA (mattress category proven) |
| **E&I Cooperative Services** | JAGGAER | ✅ complete (2026-06-22) | — | mattress, bedding, furniture, dorm/residence hall | Higher-ed; University Sleep Products mattress contract |
| **Sourcewell** | Sourcewell Procurement Portal | ✅ confirmed (2026-06-24) | — | furniture/dorm | Monitor 2027 furniture re-bid |
| **Choice Partners / HCDE** | IonWave | 🟡 **UNBLOCKED — register now** (SAM Active 2026-07-17) | — | FF&E, dorm furniture | Was UEI-gated; gate cleared 2026-07-17 (SAM Active under the LLC). Register on IonWave and cite UEI `XF73FG8CVMX1`. |
| **BuyBoard** (TASB) | IonWave | ⬜ target | — | NIGP 205/420 | Contract #767 names dormitory furniture; register to be positioned |
| **HGACBuy** | — | ⛔ skip | — | — | No furniture/mattress category exists |

## Other state boards (OK / LA / MS / AR / NM)

| State / buyer | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **Oklahoma OMES** | OMES Supplier Portal | ✅ submitted (2026-06-20) | Reg ID **0000018606** | mattress, bedding, correctional, dorm; NIGP 205/420 | OK state agencies incl. ODOC |
| **Louisiana OSP** | LaGov Supplier Self-Service | ✅ complete (2026-06-20) | — | mattress, bedding, dorm, correctional, FF&E | LaPAC notifications |
| **Mississippi DFA** | MAGIC Supplier Self-Service | ✅ complete (2026-06-20) | — | mattress, dorm furniture, bedding, FF&E | Bid the FY26-27 "Furniture–Cafeteria/Dormitory" contract |
| **Arkansas OSP** | ARBuy (Periscope/BSO) | ✅ complete (2026-06-21) | — | mattress, bedding, beds, correctional/dorm | AR Division of Correction, universities |
| **New Mexico GSD/SPD** | eProNM/JAGGAER + Euna/Bonfire | ✅ complete (2026-06-27) | acct **beford@silverlinesleep.com** (Euna Supplier Network exposes no numeric vendor ID) | mattress, bedding, dorm, FF&E (15-code NIGP/UNSPSC set) | Euna/Bonfire NM-SPD portal registration complete (all 4 steps); eProNM + Euna both covered. Opportunity Recommendations = Daily → funnel; Invites + Messages on. Commodity set = UNSPSC mattresses/patient beds/mattress pads/overlays + NIGP 420 furniture family + 850 mattress covers/pads/protectors (animal-bedding 32508 removed). **VERIFIED 2026-06-28:** no "L.P." anywhere; Euna Supplier Network Business Profile reads "Continental Silverline LLC" and propagates to NM-SPD. No legal-name fix needed. Runbook: [`nm_spd_euna_bonfire_registration_runbook.md`](nm_spd_euna_bonfire_registration_runbook.md) |

## Counties / local (jails, detention)

| Buyer | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **New Orleans / Orleans Parish (BRASS)** | Infor Supply Management | ✅ complete | Supplier **13390** | commodity-code notifications active | Jail/shelter coverage |
| **East Baton Rouge Parish** | Vendor Self Service / Central Bidding | ✅ complete | Vendor **1099** | commodities added | NOTE: legacy vendor-record email differs — monitor both routing paths |
| **Bexar County (San Antonio)** | Infor Supplier Portal | ✅ registered | Supplier **17427** | institutional/bedding | Large jail; recurring replacement |
| **El Paso County** | IonWave | ✅ activated (2026-06-22) | — | mattress/bedding/correctional | Border-region jail |
| **Tarrant County (Fort Worth)** | IonWave | ✅ registered | — | jail/institutional | Large urban jail |
| **Dallas County** | BidNet Direct | ✅ via BidNet six-state | — | NIGP-matched | Covered by the BidNet TX group |
| **BidNet Direct — TX/LA/AR/MS/NM/OK** | BidNet Direct | ✅ six-state profile configured | — | NIGP 42068 + bed/bedding | Aggregates many local agencies |
| **Walker County (Huntsville/TDCJ HQ)** | Bonfire | ✅ RSS-monitored | — | — | Feed in `configs/feeds.json`; register for commodity alerts if needed |

## Universities (residence life)

| Buyer | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **Texas A&M System (AggieBid)** | JAGGAER/SciQuest | ✅ confirmed (2026-06-22) | — | residence hall, Twin XL, dorm furniture, mattress | ~11,000+ beds |
| **University of Oklahoma** | JAGGAER (OUHSC) | ✅ complete (2026-06-24) | — | mattress/dorm/residence hall | Norman housing base |
| **Oklahoma State University** | JAGGAER (OSU) | ✅ complete (2026-06-24) | — | mattress/dorm/residence hall | Stillwater residential system |
| **Louisiana State University** | LaPAC (dept enrollment) | ✅ via LaPAC | — | dorm/student-housing FF&E | LSU posts via LaPAC; enrolled suppliers get notices |
| **UT Austin** | UT Austin Vendor Portal (Procurement Services) + ESBD agency code **721** | ⬜ target — VMO intro meeting done | — | mattress/dorm/residence hall; UHD (Housing & Dining) | VMO intro meeting held; follow-up email 2026-07-13 with portal/resource list. Register on the vendor portal, add ESBD agency-721 saved search (ESBD already ✅). UHD = housing buyer; minor projects <$10M post via Planning, Design & Construction. HBP 7.5.2 D1 lets UT buy from existing contracts → E&I / TIPS / Region 4-OMNIA are alternate routes. Category mgr contact (Med/Lab/Nat Sci): Michelle Bernal. Lead Radar: `ut-austin-vendor-portal-uhd-watch` |

---

## How to use this ledger
- **Starting a bid?** Find the buyer's portal here for the login path, account ID, and commodity setup already in place.
- **Notifications not arriving?** Confirm the portal's notification address is `beford@silverlinesleep.com` and that it's forwarding into the funnel.
- **Keep it current:** when a new registration completes (or a portal issues a vendor number), update the matching row here **and** the source's Lead Radar note so the two stay in sync.

### Open registration tasks (next up)
1. ~~Watch SAM.gov validation emails~~ ✅ **ACTIVE 2026-07-17.** Registration complete under the LLC; UEI `XF73FG8CVMX1` is citable on bids. Remaining housekeeping: **record the CAGE code in the Federal table above** (from the activation notice in the silverlinesleep.com inbox). Pipeline unblocked same day (JBSA row + recurring federal channels).
2. **Choice Partners / HCDE — register now** (unblocked 2026-07-17; cite the UEI).
3. **BuyBoard** vendor application (position for contract #767, dormitory furniture).
3a. **UT Austin vendor portal** — register (VMO follow-up received 2026-07-13) and add an ESBD saved search for agency code **721**; then identify the UHD/housing FF&E buyer (only the Med/Lab category manager contact is in hand).
4. ~~**New Mexico** — Euna/Bonfire NM-SPD registration~~ ✅ **verified 2026-06-28**. Euna/NM-SPD already shows LLC; no L.P. correction is needed.
5. **Fix the legal entity everywhere** (L.P. → LLC) per [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md): repo done; online portals are the operator checklist (SAM first).

### Scope note
Docs only. No code/CSV/config changes. Account IDs listed are non-secret portal identifiers already recorded in `leads/review/_lead_radar.csv`; CMBL number, EIN, phone, and street address remain out of version control.
