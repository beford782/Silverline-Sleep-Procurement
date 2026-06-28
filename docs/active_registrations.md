# Active Registrations Ledger — Continental Silverline Products, LLC

- **For:** Blake / Continental Silverline Products, LLC (Houston, TX)
- **Last updated:** 2026-06-27
- **Purpose:** Single source of truth for **where we are registered to bid**, so any new pursuit can pull the right portal, login, and commodity setup at a glance. Consolidates registration status previously scattered across `leads/review/_lead_radar.csv` notes and `vendor-profiles/`.

> **Notification mailbox:** all portals point to the business mailbox **beford@silverlinesleep.com**, which forwards into the ingest funnel (Power Automate → `ingest_email.py` → `relevance.py` → pipeline/Lead Radar). See [`email_ingest_setup.md`](email_ingest_setup.md).
>
> **PII rule:** vendor account numbers shown below are non-secret portal IDs (not passwords). The **CMBL number, EIN, phone, and street address are kept OUT of version control** — they live in the operator's records / local memory, shown here as `[on file]`.

**Status legend:** ✅ active/confirmed · 🟡 in progress · ⬜ target (not yet registered) · ⛔ skip (no fit)

---

## Federal

| Buyer / vehicle | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **SAM.gov** (all federal contracts) | SAM.gov | 🔴 **WRONG ENTITY — must re-register** | UEI **XF73FG8CVMX1** is the **L.P.'s** (abandon) | NAICS 337910/337127; PSC 7210/7105 | **The existing SAM registration + UEI were created for CONTINENTAL SILVERLINE PRODUCTS, L.P. — a nonexistent entity.** Do **NOT** complete EFT/banking; do **NOT** cite this UEI. The real **LLC** needs a FRESH SAM registration under its own EIN (new UEI/CAGE). First: open an FSD ticket. Saved-search alerts (NAICS 337910 / PSC 7210 / mattress) stay on. Runbook: [`sam_uei_unblock_runbook.md`](sam_uei_unblock_runbook.md) |

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
| **Choice Partners / HCDE** | IonWave | 🟡 deferred → **resume now** | — | FF&E, dorm furniture | Was UEI-gated; **UEI now assigned** → complete registration |
| **BuyBoard** (TASB) | IonWave | ⬜ target | — | NIGP 205/420 | Contract #767 names dormitory furniture; register to be positioned |
| **HGACBuy** | — | ⛔ skip | — | — | No furniture/mattress category exists |

## Other state boards (OK / LA / MS / AR / NM)

| State / buyer | Platform | Status | Account ID | Commodity setup | Notes |
|---|---|---|---|---|---|
| **Oklahoma OMES** | OMES Supplier Portal | ✅ submitted (2026-06-20) | Reg ID **0000018606** | mattress, bedding, correctional, dorm; NIGP 205/420 | OK state agencies incl. ODOC |
| **Louisiana OSP** | LaGov Supplier Self-Service | ✅ complete (2026-06-20) | — | mattress, bedding, dorm, correctional, FF&E | LaPAC notifications |
| **Mississippi DFA** | MAGIC Supplier Self-Service | ✅ complete (2026-06-20) | — | mattress, dorm furniture, bedding, FF&E | Bid the FY26-27 "Furniture–Cafeteria/Dormitory" contract |
| **Arkansas OSP** | ARBuy (Periscope/BSO) | ✅ complete (2026-06-21) | — | mattress, bedding, beds, correctional/dorm | AR Division of Correction, universities |
| **New Mexico GSD/SPD** | eProNM/JAGGAER + Euna/Bonfire | ✅ complete (2026-06-27) | acct **beford@silverlinesleep.com** (Euna Supplier Network exposes no numeric vendor ID) | mattress, bedding, dorm, FF&E (15-code NIGP/UNSPSC set) | Euna/Bonfire NM-SPD portal registration complete (all 4 steps); eProNM + Euna both covered. Opportunity Recommendations = Daily → funnel; Invites + Messages on. Commodity set = UNSPSC mattresses/patient beds/mattress pads/overlays + NIGP 420 furniture family + 850 mattress covers/pads/protectors (animal-bedding 32508 removed). **Follow-up:** the Euna profile's "Continental Silverline LLC" is **CORRECT — leave it.** Instead, edit the **NM-SPD tenant** vendor record (submitted as "L.P." this session) to the LLC. (SAM/UEI is the wrong L.P. entity — see the SAM row.) Runbook: [`nm_spd_euna_bonfire_registration_runbook.md`](nm_spd_euna_bonfire_registration_runbook.md) |

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

---

## How to use this ledger
- **Starting a bid?** Find the buyer's portal here for the login path, account ID, and commodity setup already in place.
- **Notifications not arriving?** Confirm the portal's notification address is `beford@silverlinesleep.com` and that it's forwarding into the funnel.
- **Keep it current:** when a new registration completes (or a portal issues a vendor number), update the matching row here **and** the source's Lead Radar note so the two stay in sync.

### Open registration tasks (next up)
1. **RE-REGISTER SAM.gov for the LLC.** The existing registration + UEI XF73FG8CVMX1 are the wrong (nonexistent) L.P. entity — **do NOT complete EFT/banking on it.** Open an FSD ticket and register the LLC fresh under its own EIN (new UEI/CAGE). Saved-search alerts (NAICS 337910 / PSC 7210 / mattress) stay enabled.
2. **Resume Choice Partners / HCDE** (UEI now available).
3. **BuyBoard** vendor application (position for contract #767, dormitory furniture).
4. ~~**New Mexico** — Euna/Bonfire NM-SPD registration~~ ✅ **done 2026-06-27**. Correction: the Euna profile's "Continental Silverline LLC" is **CORRECT — do NOT change it.** Instead, edit the **NM-SPD tenant** vendor record (submitted as "L.P." this session) to the LLC.
5. **Fix the legal entity everywhere** (L.P. → LLC) per [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md): repo done; online portals are the operator checklist (SAM first).

### Scope note
Docs only. No code/CSV/config changes. Account IDs listed are non-secret portal identifiers already recorded in `leads/review/_lead_radar.csv`; CMBL number, EIN, phone, and street address remain out of version control.
