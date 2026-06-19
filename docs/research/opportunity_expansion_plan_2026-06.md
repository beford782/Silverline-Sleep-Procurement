# Opportunity & Source Expansion Plan — Continental Silverline

**Date:** 2026-06-18
**Scope:** Institutional mattress, bedding, dormitory, correctional, shelter, and furniture/FF&E contract opportunities across **TX / OK / LA / MS / AR / NM**.
**Status:** Discovery & strategy sprint — **research only**. No code, no parser adapters, no active-pipeline changes, no Contract Vehicle Watch implementation. All recommendations below are *proposals* for human review.

> **URL & verification legend.** This report follows the repo's URL-caution rule (`sources/README.md`): do not act on invented URLs.
> - **VERIFIED** — the page/feed was fetched live during research (June 2026).
> - **PATTERN** — high-confidence by a known URL pattern (e.g. Bonfire `/opportunities/rss`) but the specific endpoint was not individually fetched; confirm it returns `200` + valid content before committing.
> - **UNVERIFIED** — the buyer/vehicle is confirmed real but the exact procurement URL/portal was not confirmed in-session; verify before outreach or before adding to `sources/`.

---

## Executive summary

The current monitored set is **20 sources** (7 state boards, Houston-area city/county/ISD + 3 universities, 6 national co-ops) and **only 3 RSS feeds** (Bonfire: Harris County, UT Austin, UT Health San Antonio). The biggest, cheapest expansion is **Bonfire RSS**: every Bonfire tenant exposes a working `https://<tenant>.bonfirehub.com/opportunities/rss` feed, so each newly discovered Bonfire buyer is a near-zero-cost feed add that flows straight through the existing `ingest_rss.py` → relevance → ACCEPT/REVIEW routing.

Highest-leverage findings:

1. **TDCJ runs on Bonfire** (`tdcj.bonfirehub.com`) with a **live RSS feed** — the single highest-value mattress/bedding target in the region (largest US state prison system, mattresses are a continual consumable). **Add this feed first.**
2. **11 verified-live Bonfire RSS feeds** are ready to drop into `configs/feeds.json` today (TDCJ, Dallas Housing Authority, Opportunity Home San Antonio, UT-RGV, UT-Tyler, Houston Community College, Tarrant County College, City of Fort Worth, City of Dallas, Houston METRO, Mississippi IHL).
3. **Co-op vendor entry** has clear winnable targets with **proven mattress/dorm categories**: OMNIA/Region 4 ESC (named mattress incumbent exists), Equalis Group (mattress white space, TX lead agency), **Mississippi DFA "Furniture–Cafeteria/Dormitory"** (multi-vendor, out-of-state-friendly, annual cycle = most winnable near-term), TIPS (re-bids ~yearly), BuyBoard (#767 literally names "Dormitory").
4. **E&I + Louisiana** already have *named mattress* awards (Sysco Guest Supply on E&I; Grand Bedding on LA state contract) — these define the competitive landscape and the renewal windows to monitor.

The non-TX states (OK/LA/MS/AR/NM) yield few RSS wins; the highest-leverage way to reach them is **(a) a single national co-op award** (OMNIA/TIPS/Equalis/Sourcewell grant pass-through eligibility in all six states) plus **(b) the state boards already tracked** and **BidNet group registrations** (OK, TX) that aggregate many small local agencies.

---

## Lane 1 — Top 25 new sources/portals to monitor

Ranked by mattress/dorm/correctional/FF&E relevance × geographic fit (TX heaviest) × intake ease (RSS > saved search > login). Already-monitored sources excluded.

| Rank | Source | Platform | State | Buyer type | URL | Verify | RSS? | Why high-value | Intake |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **TDCJ** | Bonfire | TX | corrections | `tdcj.bonfirehub.com/portal/` | VERIFIED | **yes** | Largest TX prison system; live feed shows cotton batting, inmate housing | rss |
| 2 | Dallas Housing Authority | Bonfire | TX | housing authority | `dhantx.bonfirehub.com/portal/` | VERIFIED | yes | Unit renovation/furnishing buys | rss |
| 3 | Opportunity Home San Antonio | Bonfire | TX | housing authority | `homesa.bonfirehub.com/portal/` | VERIFIED | yes | Largest TX PHA; apartment furnishings | rss |
| 4 | UT Rio Grande Valley | Bonfire | TX | university | `utrgv.bonfirehub.com/portal/` | VERIFIED | yes | Large dorm/residence-life footprint | rss |
| 5 | UT Tyler | Bonfire | TX | university | `uttyler.bonfirehub.com/portal/` | VERIFIED | yes | Residence-hall FF&E/bedding | rss |
| 6 | UT Dallas | Bonfire | TX | university | `utdallas.bonfirehub.com/portal/` | PATTERN | yes | Growing on-campus housing | rss |
| 7 | **Region 4 ESC** (OMNIA lead agency) | IonWave | TX | co-op/ESC | `region4esc.ionwave.net` | VERIFIED | no | Largest TX co-op; statewide furniture/dorm/FF&E awards | email_notification |
| 8 | Houston Community College | Bonfire | TX | college | `hccs.bonfirehub.com/portal/` | VERIFIED | yes | Home-market campus FF&E | rss |
| 9 | Mississippi IHL (all MS public univ.) | Bonfire | MS | university system | `msihl.bonfirehub.com/portal/` | VERIFIED | yes | One feed covers all MS public-university dorms | rss |
| 10 | Tarrant County College District | Bonfire | TX | college | `tccd.bonfirehub.com/portal/` | VERIFIED | yes | DFW college FF&E/dorm services | rss |
| 11 | City of Fort Worth | Bonfire | TX | city | `fortworthtexas.bonfirehub.com/portal/` | VERIFIED | yes | Large city; shelter/jail/FF&E | rss |
| 12 | City of Dallas | Bonfire | TX | city | `dallascityhall.bonfirehub.com/portal/` | VERIFIED | yes | Major city procurement volume | rss |
| 13 | Texas Facilities Commission (TFC) | Bonfire | TX | state/FF&E | `tfcstate.bonfirehub.com/portal/` | PATTERN | yes | Statewide furniture/FF&E + surplus | rss |
| 14 | Walker County, TX | DemandStar | TX | county | DemandStar agency page | VERIFIED | no | Huntsville (TDCJ HQ); jail/institutional bedding | portal_registration |
| 15 | Brazoria County, TX | Bonfire | TX | county | `brazoriacountytx.bonfirehub.com/portal/` | PATTERN | yes | Gulf Coast county; jail/FF&E | rss |
| 16 | Houston METRO | Bonfire | TX | transit agency | `ridemetro.bonfirehub.com/portal/` | VERIFIED | yes | Houston-market facilities/FF&E adjacency | rss |
| 17 | City of Stillwater, OK | IonWave | OK | city | `stillwater.ionwave.net` | VERIFIED | no | OK city + OSU-adjacent institutional buys | email_notification |
| 18 | BidNet Direct — Oklahoma Group | BidNet | OK | multi-agency | `bidnetdirect.com/oklahoma` | VERIFIED | no | One registration aggregates OK counties/cities/ISDs | portal_registration |
| 19 | BidNet Direct — Texas Group | BidNet | TX | multi-agency | `bidnetdirect.com/texas` | VERIFIED | no | Aggregates smaller TX locals not elsewhere monitored | portal_registration |
| 20 | South Texas College | Bonfire | TX | college | `southtexascollege.bonfirehub.com/portal/` | PATTERN | yes | RGV college campus FF&E | rss |
| 21 | Hood County, TX | Bonfire | TX | county | subdomain UNVERIFIED | UNVERIFIED | yes | County jail/FF&E | rss |
| 22 | City of Greenville, TX | OpenGov | TX | city | `procurement.opengov.com` (agency page UNVERIFIED) | UNVERIFIED | no | Confirmed OpenGov adopter; small-city FF&E | saved_search |
| 23 | Ector County, TX | OpenGov | TX | county | `procurement.opengov.com` (agency page UNVERIFIED) | UNVERIFIED | no | Jail/FF&E | saved_search |
| 24 | Texas Workforce Commission | Bonfire | TX | state agency | `twc-texas-gov.bonfirehub.com/portal/` | PATTERN | yes | Shelter/residential-program FF&E adjacency | rss |
| 25 | New Mexico State University | JAGGAER/SciQuest | NM | university | `bids.sciquest.com/.../PublicEvent?CustomerOrg=NMSU` | VERIFIED | no | Best NM dorm-heavy target; public event browse | portal_registration |

**RSS-ready shortlist (verified live — cheapest wins):** TDCJ, Dallas Housing Authority, Opportunity Home San Antonio, UT-RGV, UT-Tyler, Houston Community College, Tarrant County College, City of Fort Worth, City of Dallas, Houston METRO, Mississippi IHL. (Exact feed URLs in §5.)

**Pattern-confirmed, verify the feed before adding:** UT Dallas, Texas Facilities Commission, Brazoria County, South Texas College, TWC, Hood County.

**Registration / saved-search only (no public RSS):** Region 4 ESC (IonWave), City of Stillwater OK (IonWave), BidNet OK Group, BidNet TX Group, DemandStar/Walker County, OpenGov (Greenville/Ector), NMSU (JAGGAER).

**Honesty notes:** `habc.bonfirehub.com` is the Housing Authority of *Baltimore City* — **do not add** (not Houston). IonWave/DemandStar/BidNet/OpenGov have **no public RSS** (registration/saved-search only). LA universities post through **LaPAC** (already tracked), so LA yields few net-new portal targets.

---

## Lane 2 — Top 50 buyers worth tracking

Single global rank, grouped by cluster. URLs marked UNVERIFIED are confirmed-real buyers whose exact bids page needs confirmation before outreach. Most **TX state agencies route formal solicitations through ESBD/TxSmartBuy** (already tracked) — that one board is the highest-leverage TX state-agency monitor; non-TX state agencies route through OMES (OK) / LaPAC (LA) / MAGIC (MS) / ARBuy (AR) / NM SPD.

### State corrections (largest standing bed counts)
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 1 | Texas Dept. of Criminal Justice (TDCJ) | TX | ~130k inmates; mattresses a continual consumable | Bonfire `tdcj.bonfirehub.com` + ESBD |
| 6 | Louisiana DPS&C | LA | High incarceration; statewide refresh cycles | LaPAC (UNVERIFIED agency) |
| 7 | Mississippi DOC (MDOC) | MS | Highest US imprisonment rate; Parchman + facilities | MAGIC — `mdoc.ms.gov/general-public/procurement` |
| 8 | Oklahoma DOC (ODOC) | OK | ~23.5k inmates; large bedding base | OMES |
| 9 | Arkansas Division of Correction | AR | Expanding capacity; active procurement page | `doc.arkansas.gov/procurement/` |
| 12 | New Mexico Corrections Dept. | NM | Statewide; recurring bedding | NM SPD (UNVERIFIED) |

### County jails / sheriff
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 3 | Dallas County Sheriff / Jail | TX | ~7,100 beds; high turnover | UNVERIFIED (likely IonWave/Euna) |
| 4 | Bexar County (San Antonio) ADC | TX | 4,000+ beds | UNVERIFIED |
| 5 | Tarrant County (Fort Worth) Jail | TX | ~5,000-bed complex | UNVERIFIED |
| 18 | Travis County (Austin) Jail | TX | Large urban jail | UNVERIFIED |
| 19 | Oklahoma County Detention (OKC) | OK | Capacity/replacement pressure | UNVERIFIED |
| 20 | El Paso County Detention | TX | Large border-region jail | UNVERIFIED |
| 21 | Orleans Parish Sheriff (New Orleans) | LA | Consent-decree upgrades | UNVERIFIED |
| 22 | East Baton Rouge Parish Prison | LA | Replacement facility planning | UNVERIFIED |
| 23 | Hinds County / Raymond Detention (Jackson) | MS | Consent-decree refresh | UNVERIFIED |
| 24 | Pulaski County (Little Rock) Detention | AR | Largest AR county jail | UNVERIFIED |
| 25 | Texas Commission on Jail Standards | TX | *Lead-gen, not a buyer* — facility list drives jail specs | `tcjs.state.tx.us` |

### Juvenile detention
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 10 | Texas Juvenile Justice Dept. (TJJD) | TX | 5 secure + 5 halfway facilities; recurring bedding | ESBD (UNVERIFIED) |
| 26 | OK Office of Juvenile Affairs | OK | State juvenile residential facilities | OMES (UNVERIFIED) |
| 27 | Harris County Juvenile Probation | TX | Large juvenile detention; distinct procurement | UNVERIFIED |

### Universities / residence life
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 2 | Texas A&M University (College Station) | TX | 11,000+ beds + 2,600 Corps; summer refresh | AggieBuy/Jaggaer |
| 11 | Texas State University System | TX | ~9,000→11,300 beds by 2027; new halls = FF&E | Jaggaer/SciQuest (VERIFIED) |
| 13 | Texas Tech University | TX | ~18 halls; recurring refresh | UNVERIFIED |
| 14 | Sam Houston State University | TX | ~4,500 beds; new hall construction | TSUS portal |
| 15 | Louisiana State University (LSU) | LA | New halls broke ground Dec 2025 = fresh FF&E | UNVERIFIED |
| 16 | University of Oklahoma (OU) | OK | New South/North halls under construction | UNVERIFIED |
| 17 | Oklahoma State University (OSU) | OK | Large Stillwater system | UNVERIFIED |
| 28 | University of Arkansas (Fayetteville) | AR | Pomfret ~800 + large system | `procurement.uark.edu` |
| 29 | University of Mississippi (Ole Miss) | MS | Large hall system | `procurement.olemiss.edu` |
| 30 | Mississippi State University | MS | Large Starkville base | `procurement.msstate.edu` |
| 31 | University of New Mexico (UNM) | NM | Coronado + halls, Albuquerque | `purchasing.unm.edu` |
| 32 | New Mexico State University (NMSU) | NM | ~3,269 beds; new Juniper hall | SciQuest (VERIFIED) |
| 33 | University of North Texas (Denton) | TX | Large DFW residential base | `untsystem.edu/procurement` |
| 34 | Texas Woman's University (Denton) | TX | Residential campus | UNVERIFIED |
| 35 | University of Louisiana at Lafayette | LA | Largest UL System campus | LaPAC-linked |
| 36 | Southeastern Louisiana University | LA | Residential Hammond campus | UNVERIFIED |
| 37 | University of Central Oklahoma | OK | Residential metro campus | UNVERIFIED |
| 38 | Arkansas State University (Jonesboro) | AR | Large residential campus | `astate.edu/a/procurement/` |

### Community colleges with dorms
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 39 | Blinn College (Brenham) | TX | ~1,800 on-campus beds — most of any TX CC | UNVERIFIED |
| 40 | Wharton County Junior College | TX | ~129 dorm beds | UNVERIFIED |
| 41 | Frank Phillips College (Borger) | TX | Confirmed on-campus housing | UNVERIFIED |
| 42 | Northeastern Oklahoma A&M (Miami, OK) | OK | Residential two-year college | UNVERIFIED |

### K-12 residential / boarding
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 43 | Texas School for the Deaf (Austin) | TX | State residential school; boarding dorms | ESBD |
| 44 | Texas School for the Blind & Visually Impaired | TX | Dormitory housing | ESBD |
| 45 | Oklahoma School of Science & Mathematics | OK | Statewide residential STEM academy | UNVERIFIED |
| 46 | Mississippi School for the Deaf / Blind | MS | State residential schools | MAGIC |

### Behavioral health / state hospitals / SSLCs
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 47 | Texas HHSC — State Hospitals & SSLCs | TX | 9 hospitals + 13 SSLCs; **active bed expansion** (SA 300-bed, Rusk +200, Kerrville 2027); published forecast | ESBD |
| 48 | Oklahoma Dept. of Mental Health & SAS | OK | State psychiatric/residential beds | OMES |
| 49 | LA / MS / AR state hospital systems | LA/MS/AR | State psychiatric/residential beds (e.g. MS State Hospital at Whitfield; AR State Hospital) | LaPAC / MAGIC / AR |

### Housing authorities & emergency/shelter (lower conviction — less predictable bedding cycles)
| Rank | Buyer | State | Why | Portal |
|---|---|---|---|---|
| 50 | Opportunity Home San Antonio | TX | Largest TX PHA (MTW); furnishes some/senior units | Bonfire `homesa` |
| + | Dallas Housing Authority | TX | Major metro PHA; furnished/senior units | Bonfire `dhantx` |
| + | Texas Division of Emergency Management (TDEM) | TX | Mass-care sheltering (cots/bedding); Gulf Coast stockpiling | ESBD |

### Highest-conviction 10 (most likely to solicit in next 12–18 months)
1. **TDCJ (TX)** — continual mattress consumable; trackable via Bonfire + ESBD.
2. **Texas HHSC State Hospitals/SSLCs (TX)** — active bed-expansion pipeline; published forecast.
3. **Texas A&M (TX)** — 11,000+ beds on a summer refresh cycle.
4. **Texas State University System (TX)** — growing to 11,300 beds by 2027; new halls.
5. **Dallas County Jail (TX)** — ~7,100 beds, high turnover.
6. **LSU (LA)** — new residence halls broke ground Dec 2025 (imminent FF&E).
7. **University of Oklahoma (OK)** — two new halls under construction.
8. **TJJD (TX)** — multiple secure residential facilities; recurring refresh.
9. **Bexar County Jail (TX)** — 4,000+ beds; recurring replacement.
10. **Mississippi DOC (MS)** — highest US imprisonment rate; aging facilities; active page.

---

## Lane 3 — Top contract vehicles / co-ops to investigate

*"VERIFIED" pages were fetched; co-op contract numbers/dates/incumbents are largely **INFERRED** (TIPS/OMNIA/Equalis/1GPA domains block automated fetch) — confirm on the live catalog before relying.*

### Tier A — APPLY to become an awarded vendor (active path / favorable structure)
1. **OMNIA Partners (via Region 4 ESC, Houston)** — largest national co-op, **local TX lead agency**, **proven mattress category** (named incumbent: Gateway Mattress). Register on Region 4 IonWave; watch for the next furniture/student-housing RFP. *Highest reward.*
2. **Equalis Group (via Region 10 ESC, Richardson TX)** — TX lead agency, documented Bonfire RFP process, furniture category with **no entrenched mattress incumbent = white space**. Watch `equalisgroup.org/current-solicitations`.
3. **Mississippi DFA "Furniture–Cafeteria/Dormitory" statewide** — **most winnable near-term**: nonexclusive multi-vendor, explicit dorm + mattress categories, out-of-state vendors already win, **annual FY cycle** (FY26-27 solicitation likely spring 2026). Register in MAGIC.
4. **TIPS (Region 8 ESC)** — **best timing** (furniture re-solicited ~yearly). Register in TIPS IonWave; respond to next "Furniture, Furnishings & Services" RFP.
5. **BuyBoard (#767 "…and Dormitory")** — strongest dorm-furniture category naming; next furniture re-bid ~2028, so register now to be positioned/alerted.

### Tier B — MONITOR for re-solicitation (category just awarded or timing-dependent)
6. **ESC Region 19 / Allied States Coop (El Paso TX)** — furnishings RFP appears **due for re-solicitation (~2024–25)**; national reach.
7. **Choice Partners (HCDE, Houston)** — FF&E re-bid ~late 2026–2027; good for bed frames/FF&E (no mattress line yet).
8. **Louisiana OSP** — **named in-state mattress incumbent (Grand Bedding)** + dorm/corrections furniture (Norix, possible 9/2025 expiry); verify expirations and watch eCat for re-bid.
9. **E&I Cooperative Services (higher-ed)** — best dorm-mattress *audience*; **Sysco Guest Supply mattress contract just re-awarded (2026–2029)** so register for alerts and target the next residence-life RFP.
10. **Sourcewell** — furniture awarded 2023; monitor ~2027 re-solicitation.
11. **NCPA / 1GPA** — furniture contracts at/near expiry (~2025); check in-progress re-bids (NCPA overlaps OMNIA).

### Tier C — Conditional / niche
- **Vizient Value First (non-acute/LTC)** then **Premier** — only if Continental markets a **healthcare support-surface line**; Vizient has a verified "Beds, Mattresses & Overlays" category (lower-barrier non-acute door).
- **TXMAS** — worth it **only with a GSA Schedule** (prerequisite); June 2026 quarterly Offer-Packet window open. State-agency mattress volume is ceilinged by the **TCI/WorkQuest set-aside**.
- **OK OMES / AR ARBuy / NM Bonfire** — register (free/cheap), but the highest-leverage reach into OK/AR/LA/MS/NM is a **single national co-op award** (OMNIA/TIPS/Equalis/Sourcewell) granting pass-through eligibility.

**Skip:** **HGACBuy** (no furniture/FF&E category exists — VERIFIED), **EPIC6 / PEPPM / PACE** (poor fit / TX-only / tech-centric), **"Cooperative Strategies"** (not a purchasing co-op — it's a school-planning consultancy).

### Awarded-contract intelligence (where to browse for coverage + renewal dates)
Keyword-search each catalog for **"mattress," "bedding," "dormitory," "residence hall," "FF&E"**, then record contract # + expiration and set monitoring 6–9 months ahead of each renewal:
- **TxSmartBuy contract browser** `txsmartbuy.gov/browsecontracts` (authoritative TX catalog; reveals TCI/WorkQuest set-asides).
- **OMNIA supplier directory** `omniapartners.com/suppliers` (where Gateway Mattress / Savoy / Sustainable Furniture appear).
- **Sourcewell contract search** `sourcewell-mn.gov/contract-search` (KI, Steelcase; 2027 expirations).
- **TIPS** `tips-usa.com/Vendorsbycontracts.cfm`; **BuyBoard / Choice Partners / Allied States / 1GPA / NCPA** each have a "Contracts/Awarded Vendors" page.
- **E&I catalog** — clearest single source for institutional dorm-mattress incumbents (Sysco Guest Supply, Southwest Contract; terms to 2028–2029).
- **State eCatalogs** — **Louisiana eCat/Featured Contracts** (Grand Bedding, Norix), **MS negotiated contracts** (`dfa.ms.gov/negotiated-contracts`, "Furniture–Dormitory"), **AR state contracts** (`sas.arkansas.gov/state_contracts/furniture/`), **NM Sunshine Portal** (`ssp.nm.gov`).

**Two highest-value intel items to confirm directly:** (a) OMNIA's **Gateway Mattress** contract # and term (proves an open mattress lane + identifies the competitor); (b) Louisiana's **Norix** dorm-furniture expiration (possibly re-bidding now).

---

## Lane 4 — Search query bank (by buyer cluster)

Vocabulary aligned to `tools/relevance.py` tiers (STRONG / WEAK / CONTEXT / HARD-EXCLUDE / SOFT). Every string is copy-paste usable.

### By cluster (high-signal phrases + native vocabulary)
- **Universities / dorms:** `residence hall mattress`, `dormitory mattress`, `Twin XL mattress`, `student housing mattress replacement`, `residence hall furniture`, `resident room furniture`, `dorm bed frame`, `loftable bed`, `housing FF&E`. Vocab: *Twin XL / XL twin / extra-long twin, residence hall refresh, move-in, loft/loftable/bunkable bed, res life, summer turnover.*
- **Community colleges:** `community college dormitory mattress`, `student housing mattress`, `athletic dorm beds`, `bunk bed and mattress college`, `resident room furniture refresh`. Vocab: *student/athletic/dual-credit housing, bed frame + mattress package.*
- **K-12 residential:** `boarding school mattress`, `residential school bunk bed mattress`, `bunk mattress school district`, `cot mattress school`, `residential program bedding`. Vocab: *boarding, residential campus, bunk, cot, cabin beds, residential treatment, academy housing.* (Pair with mattress/bunk/dorm to avoid desk/locker noise.)
- **County jails:** `jail mattress`, `detention mattress`, `inmate mattress`, `correctional mattress`, `suicide-resistant mattress`, `intake mattress`, `fire retardant mattress jail`, `county jail bedding`. Vocab: *intake/booking mattress, suicide-resistant/discharge-resistant/drainable, tear/slash-resistant, flame-retardant, CAL 117 / TB 117, vinyl mattress, 2-inch/4-inch detention mattress.*
- **State corrections:** `TDCJ mattress`, `correctional facility mattress`, `department of corrections mattress`, `state prison mattress`, `inmate mattress contract`, `prison bedding contract`. Vocab: *DOC, unit/offender mattress, correctional industries (in-house competitor — review), statewide term contract, DIR/co-op.*
- **Juvenile detention:** `juvenile detention mattress`, `youth detention mattress`, `secure residential mattress`, `TJJD mattress`, `suicide-resistant mattress juvenile`. Vocab: *juvenile/youth, TJJD, secure facility, residential placement, anti-ligature (SOFT — review).*
- **Emergency mgmt / shelters:** `shelter cots`, `emergency shelter mattress`, `disaster cot`, `mass care cots`, `evacuee bedding`. Vocab: *cots/folding cots, mass care/shelter, evacuee, EMA/OEM, disaster, comfort kits, surge bedding.* (Cots are WEAK — pair with shelter/emergency/disaster + a procurement cue.)
- **Housing authorities:** `housing authority mattress`, `public housing furniture and mattresses`, `transitional housing bedding`, `unit turn furniture and mattress`, `re-entry housing bedding`. Vocab: *PHA, HUD, supportive/transitional/re-entry housing, unit turn, furnished unit, FF&E.*
- **Behavioral health / residential care:** `behavioral health beds`, `psychiatric mattress`, `residential care mattress`, `group home mattress and bed frame`, `nursing home mattress`, `fluid-proof mattress`, `state hospital mattress`. Vocab: *psychiatric, state hospital, residential treatment, group home, ICF/IID, LTC/skilled nursing, fluid-proof/antimicrobial/bariatric, anti-ligature (SOFT — review).* **Biggest source of powered-hospital-bed false positives — keep medical-bed negatives attached.**

### Platform-ready

**Google Alerts (paste-ready; negatives included):**
1. `"institutional mattress" -"air mattress" -concrete -recycling -reupholster -aircraft`
2. `"correctional mattress" OR "inmate mattress" OR "jail mattress" -concrete -recycling`
3. `"detention mattress" OR "suicide-resistant mattress" -"air mattress"`
4. `"dormitory mattress" OR "residence hall mattress" OR "Twin XL mattress" -recycling`
5. `"residence hall furniture" OR "resident room furniture" -"office furniture"`
6. `"shelter cots" OR "emergency shelter mattress" OR "disaster cot" -"air mattress" -inflatable`
7. `"behavioral health beds" OR "psychiatric mattress" -"hospital bed" -"powered bed" -medical`
8. `"fire retardant mattress" OR "flame retardant mattress" -aircraft -concrete`
9. `("mattress" OR "box spring") (RFP OR RFQ OR IFB OR solicitation) Texas -"air mattress" -concrete -recycling`
10. `"FF&E" ("residence hall" OR "housing authority" OR "detention") -"office furniture"`
*Clone 2–9 per state by appending ` Oklahoma` / ` Louisiana` / ` Mississippi` / ` Arkansas` / ` "New Mexico"`. Sources = Automatic, "All results."*

**Portal saved-search keyword sets:**
- Core: `mattress; mattresses; box spring; mattress foundation; bed foundation`
- Bunk/cot: `bunk mattress; cot mattress; crib mattress; bunk bed; cots`
- Corrections: `correctional mattress; jail mattress; detention mattress; inmate mattress; intake mattress`
- Dorm: `dormitory mattress; residence hall furniture; resident room furniture; Twin XL`
- Shelter: `shelter cots; folding cots; emergency bedding; mass care`
- Broad (→ REVIEW, not auto-buy): `bedding; bed frame; furniture; furnishings; FF&E; furniture and related services`

**Commodity codes to select where portals filter by code:**
- **NIGP:** `205` Bedding/Linens/Mattresses (`205-49` mattresses, `205-50` covers/pads, `205-55` pillows); `420` Furniture: Dormitory/Household (`420-15` beds/headboards, `420-26` dormitory furniture); `425` Office furniture (SOFT — review).
- **NAICS:** `337910` Mattress Mfg (STRONG); `337127` Institutional Furniture; `337122`/`337125` household furniture (frames/bunks); `423210` Furniture Wholesalers.
- **PSC (SAM.gov/federal):** `7210` Household Furnishings (STRONG); `7105` Household Furniture; `7195` Misc Furniture; `7125` Cabinets/Lockers (SOFT).

### Guardrails (false-positive suppression)
**Hard-exclude negatives (mirror `relevance.HARD_EXCLUDE`):**
```
-"air mattress" -"air bed" -inflatable -concrete -"articulated concrete" -scour -gabion -"erosion control" -recycling -disposal -reupholster -reupholstery -refinish -aircraft -aviation
```
**Behavioral-health add-on (the requested medical-bed exclusions):**
```
-"hospital bed" -"powered bed" -"electric bed" -"med-surg bed" -"medical equipment" -stretcher -gurney
```
**Dorm/FF&E add-on (suppress office-furniture catalogs):**
```
-"office furniture" -"office supplies" -desks -"filing cabinet"
```
**Manual-review — do NOT auto-reject (SOFT, not HARD):**
- *Office/school/classroom furniture, desks, lockers* — often **bundled into the same residence-hall/detention FF&E solicitation** that buys mattresses → REVIEW.
- *Anti-ligature / ligature-resistant* — strong signal for behavioral-health/juvenile mattresses we **do** sell; only "anti-ligature hardware/doors" is out of scope → REVIEW.
- *Out-of-region* — location is often absent or names a vendor HQ; co-op contracts are usable nationwide → REVIEW (geography demotion), never hard-reject.
- *"Correctional industries" / state-made mattresses* — competitor signal, but supplemental purchase is often allowed → REVIEW.
- *Cots / bedding / furniture (WEAK-only, no explicit "mattress")* — broad co-op digests → REVIEW.

### Starter set — 10 highest-yield, lowest-false-positive queries
1. `"correctional mattress" OR "inmate mattress" OR "jail mattress" (RFP OR RFQ OR IFB OR bid) -concrete -recycling`
2. `"detention mattress" OR "suicide-resistant mattress" (solicitation OR bid) -"air mattress"`
3. `"dormitory mattress" OR "residence hall mattress" OR "Twin XL mattress" (RFP OR bid) -recycling`
4. `("mattress" OR "box spring") "residence hall furniture" -"office furniture"`
5. `"shelter cots" OR "disaster cot" OR "emergency shelter mattress" (bid OR RFP) -inflatable -"air mattress"`
6. `"behavioral health beds" OR "psychiatric mattress" (RFP OR bid) -"hospital bed" -medical`
7. `"fire retardant mattress" OR "flame retardant mattress" (correctional OR detention OR jail) -aircraft -concrete`
8. `NAICS 337910 (mattress OR bedding) (Texas OR Oklahoma OR Louisiana OR Mississippi OR Arkansas OR "New Mexico")`
9. `"housing authority" ("mattress" OR "bed frame" OR "FF&E") (RFP OR IFB) -"office furniture"`
10. `("inmate bedding" OR "correctional bedding" OR "institutional bedding") (solicitation OR contract) -recycling`

---

## 5. Recommended additions (proposals — not yet applied)

> These are **proposals** for a future implementation PR. Nothing here has been written to `configs/`, `sources/`, or any CSV. Follow the repo's rules when applying: keep JSON pretty-printed (2-space, LF), leave `official_url` empty when UNVERIFIED, and run `python -m json.tool` + the test suite.

### 5a. `configs/feeds.json` — add verified-live Bonfire RSS feeds
Highest-value first (TDCJ). These 11 were fetched live and return valid RSS 2.0 (some currently empty, which is normal). Append objects of the existing `{ "source", "url" }` shape:

```json
[
  { "source": "Bonfire: TDCJ (TX Dept. of Criminal Justice)", "url": "https://tdcj.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Dallas Housing Authority",            "url": "https://dhantx.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Opportunity Home San Antonio",        "url": "https://homesa.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: UT Rio Grande Valley",                "url": "https://utrgv.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: UT Tyler",                            "url": "https://uttyler.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Houston Community College",           "url": "https://hccs.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Tarrant County College",              "url": "https://tccd.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: City of Fort Worth",                  "url": "https://fortworthtexas.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: City of Dallas",                      "url": "https://dallascityhall.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Houston METRO",                       "url": "https://ridemetro.bonfirehub.com/opportunities/rss" },
  { "source": "Bonfire: Mississippi IHL",                     "url": "https://msihl.bonfirehub.com/opportunities/rss" }
]
```
**Verify-the-feed-then-add (PATTERN):** UT Dallas `utdallas`, Texas Facilities Commission `tfcstate`, Brazoria County `brazoriacountytx`, South Texas College `southtexascollege`, TWC `twc-texas-gov`, Hood County (confirm subdomain). Use `python tools/ingest_rss.py --feed <url> --source "Bonfire: X" --dry-run` to confirm each returns parseable XML before committing.

> Note: `ingest_rss.py` already gates everything through `relevance.py` and routes ACCEPT → active / REVIEW → Lead Radar, so these feeds need **no code change** — only the feed-list entries.

### 5b. `sources/procurement_sources.json` — add net-new registry entries
Add the following (shown abbreviated; fill all schema fields per `sources/README.md`, leave `official_url` empty + note status when UNVERIFIED). Priority order:

1. **TDCJ** — `source_type: state_portal`, intake `rss`, geography `["TX"]`, buyer_level `state`, url VERIFIED (`tdcj.bonfirehub.com`). *(Corrections; highest priority.)*
2. **Region 4 ESC (OMNIA lead agency)** — `cooperative`, intake `email_notification`, `["TX"]`/national, url VERIFIED (`region4esc.ionwave.net`).
3. **Equalis Group** — `cooperative`, intake `saved_search`, national, url VERIFIED (`equalisgroup.org`). *(Mattress white space.)*
4. **E&I Cooperative Services** — `cooperative`, intake `email_notification`, national (higher-ed), url VERIFIED (SciQuest org `EandICooperative`). *(Named dorm-mattress contract.)*
5. **ESC Region 19 / Allied States Coop** — `cooperative`, intake `saved_search`, national, url VERIFIED (`alliedstatescooperative.com`).
6. **1GPA** / **NCPA** — `cooperative`, national (NCPA via OMNIA). *(Furniture at/near expiry.)*
7. **BidNet Direct — Texas Group** and **— Oklahoma Group** — `state_portal`/aggregator, intake `portal_registration`, url VERIFIED.
8. **DemandStar (Walker County TX + commodity notifications)** — `county_portal`, intake `portal_registration`.
9. **NMSU** (`university_portal`, JAGGAER, NM) and **UNM** (NM) — dorm-heavy NM targets.
10. Corrections/dorm **buyer pages** worth their own rows once URLs are confirmed: Dallas/Bexar/Tarrant county jails, TJJD, Texas HHSC State Hospitals, LSU, OU. *(Mark UNVERIFIED until the exact bids URL is confirmed.)*

### 5c. Lead Radar manual search workflow (proposed operating procedure)
A repeatable **weekly/bi-weekly sweep** that funnels into the existing tooling without new code:

1. **Google Alerts** — stand up the 10 paste-ready alerts (§Lane 4), delivered to the Gmail funnel as **RSS feeds** ("Deliver to: RSS feed"). Add those alert-RSS URLs to `configs/feeds.json` so `ingest_rss.py` ingests them on the normal cadence (already-built path).
2. **New Bonfire RSS feeds** (§5a) — ingested automatically by `ingest_rss.py`; ACCEPT → active, REVIEW → Lead Radar.
3. **Registration-only portals** (IonWave Region 4 / Stillwater; BidNet TX/OK; DemandStar; OpenGov; JAGGAER NMSU/Texas State) — register with the §Lane 4 NIGP/commodity codes; route the resulting **email alerts** through the existing forwarded-email ingest (`ingest_email.py`, Outlook→Gmail forward funnel), which already unwraps forwarded alerts and routes by relevance band.
4. **State boards** (ESBD, OMES, LaPAC, MAGIC, ARBuy, NM) — run the §Lane 4 saved-search keyword sets on each; for TX, ESBD is the single highest-leverage state-agency monitor (TDCJ/TJJD/HHSC/TDEM/state schools all post there).
5. **Co-op contract catalogs** — quarterly, browse the awarded-contract catalogs (§Lane 3) for mattress/dorm/FF&E coverage + renewal dates; log expirations to monitor 6–9 months ahead. *(This is the manual precursor to a future Contract Vehicle Watch — not implemented in this sprint.)*
6. **Triage** — broad furniture/co-op/shelter/correctional REVIEW items stay in Lead Radar (`watching`/`reviewing`) for human confirmation; explicit mattress/product-fit ACCEPT items go to the active pipeline; promotion to active requires `lead_radar.py promote --confirmed-products`.

---

## 6. Prioritized next-action list

Grouped by action type; **P1 = do first** (cheapest/highest-yield), P2 = soon, P3 = as capacity allows.

### Add feed/source to tool (zero/low cost — RSS)
- **[P1] Add the 11 verified Bonfire RSS feeds to `configs/feeds.json`** (§5a), TDCJ first. *(Net-new mattress/dorm/correctional coverage with no code change.)*
- **[P1] Dry-run-verify then add the 6 PATTERN Bonfire feeds** (UT Dallas, TFC, Brazoria, South Texas College, TWC, Hood County).
- **[P2] Add net-new registry rows to `sources/procurement_sources.json`** (§5b), starting with TDCJ, Region 4 ESC, Equalis, E&I.

### Add alert here (Google Alerts → RSS → ingest)
- **[P1] Stand up the 10 starter Google Alerts** (§Lane 4) as RSS feeds and add to `configs/feeds.json`. Clone the corrections/dorm/shelter alerts per state.

### Register here (portals — unlock email/saved-search alerts)
- **[P1] Region 4 ESC IonWave** (`region4esc.ionwave.net`) with NIGP 205/420 codes — gateway to OMNIA + the largest TX co-op solicitations.
- **[P1] Mississippi MAGIC** supplier registration targeting the **"Furniture–Cafeteria/Dormitory"** category — most winnable near-term award (FY26-27 solicitation likely spring 2026).
- **[P2] TIPS IonWave** and **BuyBoard** vendor registration (furniture re-bid timing: TIPS ~yearly, BuyBoard ~2028).
- **[P2] BidNet TX Group + OK Group**, **DemandStar** (Walker County + commodity notifications), **Equalis Group**, **E&I** (higher-ed).
- **[P3] NMSU / Texas State (JAGGAER/SciQuest)**, OpenGov agencies (Greenville/Ector), City of Stillwater IonWave.

### Monitor this page (no registration / catalog intel)
- **[P1] TDCJ Bonfire portal + ESBD** for mattress/bedding solicitations.
- **[P2] Co-op awarded-contract catalogs** (§Lane 3) — confirm **OMNIA Gateway Mattress** term and **Louisiana Norix** expiration; log all furniture/FF&E/mattress contract renewal dates.
- **[P2] University construction pipelines** (LSU new halls, OU South/North halls, Texas State Canyon/Hilltop) — new-build FF&E buys land on delivery.
- **[P3] Texas HHSC procurement forecast PDF** for state-hospital/SSLC bed-expansion buys.

### Contact buyer / contracts office (relationship + spec intel)
- **[P2] Mississippi DFA Bureau of Purchasing** — confirm the FY26-27 "Furniture–Cafeteria/Dormitory" solicitation date and submission requirements.
- **[P2] Region 4 ESC / Equalis (Region 10 ESC)** contracts offices — confirm next furniture/student-housing RFP windows and whether a mattress line can be bid.
- **[P3] TDCJ Contracts & Procurement (BFD)** — confirm mattress/bedding spec (flame-retardant standards) and how supplemental purchases coexist with Texas Correctional Industries.
- **[P3] High-conviction dorm buyers tied to new construction** (LSU, OU housing/residence life) — introduce capability ahead of FF&E solicitations.

### Decision gate (do NOT start yet — out of sprint scope)
- **Contract Vehicle Watch** implementation (automated co-op contract-expiration monitoring) is the logical follow-on to §5c step 5, but is explicitly **deferred**. The catalog intelligence above (contract #, category, incumbent, expiration) is the manual precursor.

---

### Verification debt to close before acting
- **County-jail purchasing pages** (Dallas, Bexar, Tarrant, Travis, El Paso, OK County, Orleans, EBR, Hinds, Pulaski) — confirm exact bids URL + platform.
- **OMNIA Gateway Mattress** contract # / term; **Louisiana Grand Bedding / Norix** expirations; whether **MS / NM** list a *named* mattress category vs. rolled into "furniture"; whether the **AR legacy "Dormitory: beds & mattresses"** portal is still current.
- **PATTERN Bonfire feeds** — confirm each returns valid XML before adding.
- Co-op contract numbers/incumbents in Lane 3 are **INFERRED** (domains block automated fetch) — confirm on live catalogs.
