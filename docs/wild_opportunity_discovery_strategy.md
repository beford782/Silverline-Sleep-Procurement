# Wild Opportunity Discovery Strategy — Continental Silverline

**Date:** 2026-06-19
**Region:** TX / OK / LA / MS / AR / NM
**Type:** Strategy & research report — **not code.** No parser adapters, no active-pipeline changes, no CSV writes, no Contract Vehicle Watch implementation.

> Companion to the detailed source/buyer/vehicle research in
> [`docs/research/opportunity_expansion_plan_2026-06.md`](research/opportunity_expansion_plan_2026-06.md).
> This document is the strategic framing and the prioritized plan of attack.
>
> **Verification legend** (per `sources/README.md` URL-caution rule): **VERIFIED** = fetched live in research; **PATTERN** = high-confidence by known URL pattern, confirm before use; **UNVERIFIED** = real entity, exact procurement URL not yet confirmed.

---

## 1. Executive summary — this is a source-acquisition problem

Recent ingest volume is low. The instinct is to keep tuning the parser and the relevance classifier — but that is **not** where the shortfall is. The pipeline already:

- ingests SAM.gov, portal emails (incl. forwarded Outlook alerts), and RSS feeds;
- gates everything through a tiered relevance classifier (`tools/relevance.py`) with mattress/dorm/correctional vocabulary, NAICS 337910 / PSC 7210 awareness, and home-state geography logic;
- routes `ACCEPT → bids/active/_pipeline.csv` and `REVIEW → leads/review/_lead_radar.csv`.

The constraint is **input, not processing.** We are watching only **20 sources** and **3 RSS feeds** (Bonfire: Harris County, UT Austin, UT Health San Antonio). Institutional mattress demand is real and recurring across the six states — but most of it never reaches us because **we are not subscribed to the portals, registered with the buyers, or positioned on the contract vehicles where it is posted.**

**Low volume is a source-acquisition problem.** A better classifier cannot find an opportunity that never entered the funnel. The highest-ROI work is therefore *acquiring sources*: adding feeds, registering on portals with the right commodity codes, and getting onto co-op contracts so we are invited to the buys that never appear as a standalone public "mattress RFP." Three structural reasons the demand is hidden:

1. **It is bundled.** Mattresses ride inside broad "furniture & related services" / FF&E / "dormitory furniture" solicitations, not standalone mattress RFPs.
2. **It is bought through vehicles.** Institutions buy off co-op / vendor-pool / IDIQ contracts (BuyBoard, TIPS, OMNIA, Sourcewell). If we are not an awarded vendor, we never see the order.
3. **It is posted on portals we do not watch.** Bonfire, IonWave, BidNet, DemandStar, OpenGov instances across the six states — each a separate registration/feed.

The plan below fixes the input side. Parser/relevance work is already adequate for what is flowing in.

---

## 2. Top 25 portals / sources to monitor

Ranked by mattress/dorm/correctional/FF&E relevance × geographic fit (TX heaviest) × intake ease (RSS > saved-search > login). Excludes the 20 already-tracked sources.

| # | Source | Platform | State | Buyer type | RSS? | Verify | Why it matters |
|---|---|---|---|---|---|---|---|
| 1 | **TDCJ** (TX Dept. of Criminal Justice) | Bonfire | TX | corrections | **yes** | VERIFIED | Largest US state prison system; mattresses a continual consumable; live feed |
| 2 | Dallas Housing Authority | Bonfire | TX | housing authority | yes | VERIFIED | Unit renovation/furnishing buys |
| 3 | Opportunity Home San Antonio | Bonfire | TX | housing authority | yes | VERIFIED | Largest TX PHA; apartment furnishings |
| 4 | UT Rio Grande Valley | Bonfire | TX | university | yes | VERIFIED | Large dorm/residence-life footprint |
| 5 | UT Tyler | Bonfire | TX | university | yes | VERIFIED | Residence-hall FF&E/bedding |
| 6 | Region 4 ESC (OMNIA lead agency) | IonWave | TX | co-op/ESC | no | VERIFIED | Largest TX co-op; statewide furniture/dorm/FF&E awards |
| 7 | Houston Community College | Bonfire | TX | college | yes | VERIFIED | Home-market campus FF&E |
| 8 | Mississippi IHL (all MS public univ.) | Bonfire | MS | univ. system | yes | VERIFIED | One feed covers all MS public-university dorms |
| 9 | Tarrant County College District | Bonfire | TX | college | yes | VERIFIED | DFW college FF&E/dorm services |
| 10 | City of Fort Worth | Bonfire | TX | city | yes | VERIFIED | Shelter/jail/FF&E |
| 11 | City of Dallas | Bonfire | TX | city | yes | VERIFIED | Major-city procurement volume |
| 12 | Houston METRO | Bonfire | TX | transit agency | yes | VERIFIED | Houston facilities/FF&E adjacency |
| 13 | UT Dallas | Bonfire | TX | university | yes | PATTERN | Growing on-campus housing |
| 14 | Texas Facilities Commission | Bonfire | TX | state/FF&E | yes | PATTERN | Statewide furniture/FF&E + surplus |
| 15 | Brazoria County | Bonfire | TX | county | yes | PATTERN | Gulf Coast county jail/FF&E |
| 16 | South Texas College | Bonfire | TX | college | yes | PATTERN | RGV college campus FF&E |
| 17 | Texas Workforce Commission | Bonfire | TX | state agency | yes | PATTERN | Shelter/residential-program FF&E adjacency |
| 18 | BidNet Direct — Texas Group | BidNet | TX | multi-agency | no | VERIFIED | One registration aggregates smaller TX locals |
| 19 | BidNet Direct — Oklahoma Group | BidNet | OK | multi-agency | no | VERIFIED | Aggregates OK counties/cities/ISDs |
| 20 | City of Stillwater, OK | IonWave | OK | city | no | VERIFIED | OK city + OSU-adjacent institutional buys |
| 21 | DemandStar — Walker County, TX | DemandStar | TX | county | no | VERIFIED | Huntsville (TDCJ HQ); jail/institutional bedding |
| 22 | NMSU | JAGGAER/SciQuest | NM | university | no | VERIFIED | Best NM dorm-heavy target; public event browse |
| 23 | Hood County, TX | Bonfire | TX | county | yes | UNVERIFIED | County jail/FF&E (confirm subdomain) |
| 24 | City of Greenville, TX | OpenGov | TX | city | no | UNVERIFIED | Confirmed OpenGov adopter; small-city FF&E |
| 25 | Ector County, TX | OpenGov | TX | county | no | UNVERIFIED | Jail/FF&E |

**RSS quick-win pattern:** every Bonfire tenant exposes `https://<tenant>.bonfirehub.com/opportunities/rss` (confirmed live). 11 of the above were fetched live and are paste-ready feeds (see the companion report §5a). IonWave / BidNet / DemandStar / OpenGov have **no public RSS** — registration / saved-search only.

> Caution: `habc.bonfirehub.com` is the Housing Authority of *Baltimore City*, **not** Houston — do not add. Louisiana universities post through **LaPAC** (already tracked), so LA yields few net-new portal targets.

---

## 3. Top 50 buyer clusters to track

Grouped by cluster (largest standing bed counts and recurring replacement cycles weighted highest). Most TX state agencies route through **ESBD/TxSmartBuy** (already tracked); non-TX state agencies route through OMES (OK) / LaPAC (LA) / MAGIC (MS) / ARBuy (AR) / NM SPD.

**State corrections (highest conviction — continual mattress consumable):** TDCJ (TX), Louisiana DPS&C, Mississippi DOC, Oklahoma DOC, Arkansas Division of Correction, New Mexico Corrections Dept.

**County jails / sheriff (high turnover):** Dallas County (~7,100 beds), Bexar County (4,000+), Tarrant County (~5,000), Travis County, El Paso County, Oklahoma County, Orleans Parish, East Baton Rouge Parish, Hinds County (Jackson), Pulaski County (Little Rock). *(Texas Commission on Jail Standards — lead-gen, not a buyer: its facility list drives jail mattress specs.)*

**Juvenile detention:** Texas Juvenile Justice Dept. (TJJD), OK Office of Juvenile Affairs, Harris County Juvenile Probation.

**Universities / residence life:** Texas A&M (11,000+ beds + Corps), Texas State University System (→11,300 by 2027), Texas Tech, Sam Houston State, LSU (new halls 2025), University of Oklahoma (new halls), Oklahoma State, U of Arkansas, Ole Miss, Mississippi State, UNM, NMSU, U of North Texas, Texas Woman's, UL-Lafayette, Southeastern Louisiana, U of Central Oklahoma, Arkansas State.

**Community colleges with dorms:** Blinn College (~1,800 beds — most of any TX CC), Wharton County Junior College, Frank Phillips College, Northeastern Oklahoma A&M.

**K-12 residential / boarding:** Texas School for the Deaf, Texas School for the Blind & Visually Impaired, Oklahoma School of Science & Mathematics, Mississippi School for the Deaf/Blind.

**Behavioral health / state hospitals / SSLCs:** Texas HHSC State Hospitals & SSLCs (active bed expansion — SA 300-bed, Rusk +200, Kerrville 2027; published forecast), Oklahoma Dept. of Mental Health & SAS, LA/MS/AR state hospital systems (e.g. MS State Hospital at Whitfield, AR State Hospital).

**Housing authorities & emergency/shelter (lower-conviction, less predictable cycles):** Opportunity Home San Antonio, Dallas Housing Authority, Texas Division of Emergency Management (mass-care cots/bedding; Gulf Coast stockpiling).

### Highest-conviction 10 (next 12–18 months)
TDCJ · Texas HHSC State Hospitals/SSLCs · Texas A&M · Texas State University System · Dallas County Jail · LSU · University of Oklahoma · TJJD · Bexar County Jail · Mississippi DOC.

*(Full ranked table with per-buyer rationale and portal/URL status: companion report §Lane 2. Many county-jail and individual university procurement URLs are UNVERIFIED — confirm before outreach.)*

---

## 4. Contract vehicle strategy

The single biggest lever for "hidden" mattress demand. Institutions buy dorm/correctional/FF&E (and the mattresses inside it) off cooperative contracts; if we are an awarded vendor, we are *invited* to buys that never appear as public RFPs. Two motions: **(A) apply to become an awarded vendor** and **(B) monitor for re-solicitation / renewal** so we catch the next window.

| Vehicle | Lead agency | Mattress/dorm/FF&E category? | Motion | Priority & why |
|---|---|---|---|---|
| **BuyBoard** | TASB (TX) | **YES** — #767 "Furniture for School, Office… and **Dormitory**" (dorm explicitly named) | Apply (register now) | **HIGH** — strongest dorm-furniture category naming; next furniture re-bid ~2028, so register now to be positioned & alerted |
| **TIPS** | Region 8 ESC (TX) | YES — "Furniture, Furnishings & Services" | Apply | **HIGH** — best *timing*: furniture re-solicited ~yearly = shortest wait to bid |
| **Choice Partners** | HCDE (Houston) | Partial — FF&E (office/classroom/library); **no dorm/mattress line yet** | Monitor + apply | **MED** — local Houston; good for bed frames/FF&E; FF&E re-bid ~late 2026–2027 |
| **Sourcewell** | Sourcewell (MN gov unit) | YES — "Furniture Solutions" (dorm via KI); no dedicated mattress vendor | Monitor | **MED** — large reach but furniture awarded 2023; next master RFP ~2027 (long wait) |
| **OMNIA Partners** (via Region 4 ESC, Houston) | Region 4 ESC (TX) | **YES — a named mattress incumbent exists (Gateway Mattress)**; dorm via Savoy/Sustainable | Apply | **HIGH** — largest national co-op, **local TX lead agency**, **mattress category proven** — register on Region 4 IonWave |
| **HGACBuy** | H-GAC (Houston) | **NO** — contract list has zero furniture/FF&E/mattress (VERIFIED) | Skip / petition | **LOW** — no relevant category exists; only worth petitioning for a new FF&E category |
| **State contracts** | per state | Mixed (see below) | Apply / monitor | Varies — MS most winnable; LA has named mattress incumbent |

**State contracts (statewide term contracts / schedules):**
- **Mississippi DFA — "Furniture–Cafeteria/Dormitory"** — **most winnable near-term:** nonexclusive multi-vendor, **explicit dorm + mattress categories, out-of-state vendors already win, annual FY cycle** (FY26-27 likely solicited spring 2026). *Register in MAGIC and bid it.*
- **Louisiana OSP** — **named in-state mattress incumbent (Grand Bedding)** + dorm/corrections furniture (Norix, possible 9/2025 expiry). Monitor eCat for re-bid; verify expirations.
- **Texas (CMBL + TXMAS)** — TXMAS has office furniture but **no mattress/dorm TXMAS**; TX state-agency mattress volume is ceilinged by the **TCI/WorkQuest set-aside**. TXMAS requires a GSA base.
- **Oklahoma OMES** — furniture contract exists; **no mattress contract**, and an **OCI (Oklahoma Correctional Industries) preference** applies to state agencies — best reached via a national co-op award + OCI non-availability.
- **Arkansas / New Mexico** — easiest entry is a **national co-op award** (auto-eligible in-state); confirm whether a named state mattress contract exists.

**Net-new vehicles worth adding to the watch list:** **Equalis Group** (Region 10 ESC, TX — furniture category with **no entrenched mattress incumbent = white space**), **E&I Cooperative Services** (higher-ed — has a *named* dorm-mattress contract via Sysco Guest Supply, just re-awarded 2026–2029 → register for alerts, target next residence-life RFP), **ESC Region 19 / Allied States Coop** (furnishings RFP appears due for re-solicitation), **1GPA / NCPA** (furniture near expiry). **Skip:** PEPPM, PACE/EPIC6 (poor fit / TX-only), and "Cooperative Strategies" (a school-planning consultancy, **not** a purchasing co-op).

**Cross-state leverage:** one national co-op award (OMNIA / TIPS / Equalis / Sourcewell) grants pass-through buying eligibility in **all six states** — the cheapest way to reach OK/LA/MS/AR/NM beyond the state boards.

*(Contract numbers, incumbents, and dates are largely INFERRED — those co-op domains block automated fetch. Confirm on the live catalogs before relying.)*

---

## 5. Query bank by cluster

Vocabulary aligned to `tools/relevance.py` tiers. Append the guardrail negatives (below) on every web/Alert query.

### Dorm / student housing
`dormitory mattress` · `residence hall mattress` · `Twin XL mattress` · `student housing mattress replacement` · `residence hall furniture` · `resident room furniture` · `dorm bed frame` · `loftable bed` · `housing FF&E` · `move-in mattress refresh`
*Native vocab:* Twin XL / XL twin / extra-long twin, residence hall refresh, loft/loftable/bunkable bed, res life, summer turnover.

### Correctional / detention
`correctional mattress` · `inmate mattress` · `jail mattress` · `detention mattress` · `suicide-resistant mattress` · `intake mattress` · `fire retardant mattress` · `correctional bedding` · `TDCJ mattress` · `department of corrections mattress`
*Native vocab:* intake/booking mattress, suicide-resistant / discharge-resistant / drainable, tear/slash-resistant, flame-retardant, CAL 117 / TB 117, vinyl mattress, 2-inch/4-inch detention mattress, offender/detainee, unit/statewide term contract.

### Shelter / emergency
`shelter cots` · `emergency shelter mattress` · `disaster cot` · `mass care cots` · `folding cot and mattress` · `evacuee bedding` · `emergency bedding and cots`
*Native vocab:* cots / folding cots, mass care / mass shelter, evacuee, EMA / OEM, disaster, comfort kits, surge bedding. *(Cots are WEAK-tier — pair with shelter/emergency/disaster + a procurement cue.)*

### Public health / residential care
`behavioral health beds` · `psychiatric mattress` · `residential care mattress` · `state hospital mattress` · `group home mattress and bed frame` · `nursing home mattress` · `fluid-proof mattress` · `long-term care mattress`
*Native vocab:* psychiatric, state hospital, residential treatment, ICF/IID, skilled nursing/LTC, fluid-proof/antimicrobial/bariatric, anti-ligature (SOFT — review), resident room. **Biggest source of powered-hospital-bed false positives — always keep the medical-bed negatives attached.**

### Furniture / FF&E
`residence hall furniture` · `resident room furniture` · `dormitory furniture` · `FF&E` · `furniture and related services` · `institutional furnishings` · `bunk bed and mattress` · `bed frame and mattress package`
*Native vocab:* FF&E, casegoods, furnishings, "furniture & related services," resident room, unit turn. *(Broad — most route to REVIEW, not auto-accept; the mattress may be bundled inside.)*

### Co-op / vendor-pool
`cooperative purchasing furniture` · `vendor pool furniture` · `IDIQ furniture and furnishings` · `BuyBoard furniture dormitory` · `TIPS furniture furnishings` · `OMNIA furniture student housing` · `Sourcewell furniture solutions` · `Choice Partners FF&E` · `awarded furniture contract mattress`
*Native vocab:* cooperative, co-op, vendor pool, IDIQ, interlocal, purchasing cooperative, ESC eMarketplace, awarded contract / contract holder. *(These surface broad vehicles → route to Lead Radar as `co-op_contract_vehicle`.)*

### Platform-ready (paste once, per state where useful)
**Google Alerts (negatives included):**
1. `"correctional mattress" OR "inmate mattress" OR "jail mattress" -concrete -recycling`
2. `"dormitory mattress" OR "residence hall mattress" OR "Twin XL mattress" -recycling`
3. `"shelter cots" OR "disaster cot" OR "emergency shelter mattress" -"air mattress" -inflatable`
4. `"behavioral health beds" OR "psychiatric mattress" -"hospital bed" -"powered bed" -medical`
5. `("mattress" OR "box spring") (RFP OR RFQ OR IFB OR solicitation) Texas -"air mattress" -concrete -recycling`
6. `"FF&E" ("residence hall" OR "housing authority" OR "detention") -"office furniture"`
*(Clone per state by appending ` Oklahoma` / ` Louisiana` / ` Mississippi` / ` Arkansas` / ` "New Mexico"`. Deliver to RSS so `ingest_rss.py` picks them up.)*

**Commodity codes for portal filters:** NIGP `205` (bedding/mattresses), `420` (dormitory/household furniture); NAICS `337910` (mattress mfg), `337127` (institutional furniture); PSC `7210` (household furnishings), `7105` (household furniture).

### Federal direct lane — SAM.gov saved search (added 2026-06-24)

The query bank above is tuned for state/local/co-op portals. **Federal-direct demand is a separate, proven lane** that the 2026-06-24 scan confirmed is recurring and currently underserved: in a single week the funnel surfaced two genuine federal mattress fits (USCG Base Boston `37010PR260000078`; JBSA `FA301626Q0151`), and recurring federal buyers are now tracked in Lead Radar (VA/VHA, Bureau of Prisons, Army/DoD barracks).

> **HARD GATE:** every federal-direct opportunity is **SAM-registration gated**. UEI `XF73FG8CVMX1` was assigned on 2026-06-24, but the full All Awards entity registration is still in progress: taxpayer information has been submitted for IRS verification and financial information remains unfinished. Do not treat federal fits as bid-ready until SAM shows the entity registration active/complete.

**Repeatable monitoring recipe (free; no BidNet/HigherGov paywall needed):**
1. SAM.gov → **Search → Contract Opportunities**.
2. Filters: **NAICS `337910`** (Mattress Manufacturing) and/or **PSC `7210`** (Household Furnishings); **Status = Active** only; optionally add **NAICS `337127`** (institutional furniture) and **PSC `7105`** to widen.
3. **Save the search and create an email alert** (requires a free SAM.gov login) so new federal mattress/bed solicitations arrive without manual sweeps.
4. Recurring buyers to also alert by name: **VA / VHA (multiple VISNs)**, **DOJ Bureau of Prisons (FCIs)**, **Army MICC / AETC base contracting (barracks & billeting)**.

> Note for automated agents: SAM.gov and HigherGov opportunity lists are **JS-rendered and not reliably web-search-indexed** — a live open-opportunity list cannot be enumerated via `WebFetch`/`WebSearch`. The authoritative live list requires the interactive SAM.gov saved search above (operator task).

### Guardrails (false-positive suppression — append on web/Alert queries)
```
-"air mattress" -"air bed" -inflatable -concrete -"articulated concrete" -scour -gabion -"erosion control" -recycling -disposal -reupholster -reupholstery -refinish -aircraft -aviation
-"hospital bed" -"powered bed" -"electric bed" -"medical equipment" -stretcher -gurney
```
**Manual-review, do NOT auto-reject** (SOFT, not HARD): office/school furniture & lockers (often bundled with mattresses → REVIEW); anti-ligature (real behavioral-health/juvenile mattress signal → REVIEW); out-of-region (co-op contracts are nationwide → REVIEW, geography demotion); "correctional industries" (competitor, but supplemental buys often allowed → REVIEW); WEAK-only bedding/cots/furniture (broad digests → REVIEW).

---

## 6. Recommended routing

The existing ingest already implements this; the discipline below keeps the active pipeline strict and the broad signal in Lead Radar.

| Signal | Destination | Rule |
|---|---|---|
| **Confirmed live mattress / product-fit bid** (explicit mattress, box spring, bunk/cot/dorm/jail/correctional mattress; a real solicitation we can bid) | **Active pipeline** (`bids/active/_pipeline.csv`) | `relevance.ACCEPT` |
| **Broad furniture / co-op vehicle / buyer-intel** (FF&E, "furniture & related services," dorm furniture, co-op/IDIQ/vendor-pool, awarded-contract notices, ambiguous bedding) | **Lead Radar** (`leads/review/_lead_radar.csv`) | `relevance.REVIEW` |
| **Non-relevant / hard-exclude** (air/concrete mattress, hospital/powered beds, recycling/disposal, reupholster, aircraft) | **Dropped** | `relevance.REJECT` |

**Operating discipline:**
- Keep the **active pipeline strict** — only confirmed mattress/product-fit bids. Broad furniture/co-op rows pollute it and bury real bids.
- **Lead Radar is the home for market intelligence:** broad vehicles (lead_type `co-op_contract_vehicle`), broad furniture (`broad_furniture_ffe`), and buyer clusters (`dorm_student_housing`, `correctional_detention`, `shelter_emergency`, `public_health_residential`). Status `watching` for recurrence tracking; `reviewing` when actively triaging.
- **Promotion is human-gated:** a lead becomes an active bid only via `tools/lead_radar.py promote <lead-id> --confirmed-products "..."` — broad leads never auto-promote.
- New Bonfire RSS feeds and Google-Alert RSS feeds flow through this routing **with no code change** (`ingest_rss.py` already gates on `relevance.py`). Registration-portal email alerts flow through the forwarded-email ingest (`ingest_email.py`).

---

## 7. Prioritized next actions

In execution order. Each is source-acquisition work, not parser work.

### First — BuyBoard
Register Continental Silverline as a BuyBoard vendor and position for the **#767 "Furniture for School, Office… and Dormitory"** contract (dorm explicitly named). Even though the next furniture re-bid is ~2028, registering now puts us on the alert list and in the awarded-vendor pipeline for the largest TX local-government cooperative. **In parallel, register on the highest-reward co-ops with proven mattress/dorm categories and favorable timing:** OMNIA via **Region 4 ESC** (named mattress incumbent), **TIPS** (re-bids ~yearly), and bid the **Mississippi DFA "Furniture–Cafeteria/Dormitory"** statewide contract (most winnable near-term). *Action: register / submit vendor applications; calendar each furniture re-solicitation window.*

### Second — portal registration & feed expansion
Acquire the sources from §2:
- **Add the 11 verified-live Bonfire RSS feeds** to `configs/feeds.json` (TDCJ first) — zero-cost, no code change. Dry-run-verify and add the 6 PATTERN feeds.
- **Stand up the §5 Google Alerts as RSS feeds** and add them to `configs/feeds.json`.
- **Register on the no-RSS portals** with NIGP 205/420 + NAICS 337910 commodity codes so email alerts flow into the forwarded-email ingest: Region 4 ESC IonWave, City of Stillwater IonWave, BidNet TX & OK groups, DemandStar (Walker County + commodity notifications), Equalis, E&I, NMSU/Texas State (JAGGAER). *Action: a follow-up implementation PR adds the feed/source entries; registrations are operator tasks.*

### Third — top buyer account map
Build a buyer account map from §3, starting with the **highest-conviction 10**. For each: confirm the procurement portal/URL (close the UNVERIFIED gaps — especially county jails and individual universities), record bed counts / refresh cycles / new-construction timing, identify the contracts/purchasing contact, and note which co-op vehicles each buys through. This converts "clusters" into named, trackable accounts with a known channel (direct portal vs. co-op). *Action: a tracking doc/sheet of buyer → portal → vehicle → contact → next likely window.*

### Fourth — monthly co-op renewal watch
Stand up a **monthly manual review** of co-op and state awarded-contract catalogs (§4 and companion report §Lane 3): for each vehicle log contract #, category, incumbent vendor, and expiration date, then flag any contract renewing in the next 6–9 months. Two highest-value items to confirm first: **OMNIA's Gateway Mattress** term (proves the open mattress lane + names the competitor) and **Louisiana's Norix** dorm-furniture expiration (possibly re-bidding now). *Action: a monthly checklist + a small renewal tracker. This is the **manual precursor** to a future Contract Vehicle Watch — which remains **deferred / out of scope** for now.*

---

### Scope note
This document is research/strategy only. No code, CSV, parser-adapter, or Contract Vehicle Watch changes were made. The `configs/feeds.json` and `sources/procurement_sources.json` additions referenced above are **proposals for a separate implementation PR**, not applied here.
