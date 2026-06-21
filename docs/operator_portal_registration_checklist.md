# Operator Portal Registration & Alert Setup Checklist

- **For:** Blake / Continental Silverline (Houston, TX — institutional mattress & bedding; Texas CMBL registered)
- **Service geography:** TX / OK / LA / MS / AR / NM
- **Date:** 2026-06-19
- **Type:** Operator runbook (docs only). No code, no `configs/feeds.json` change, no CSV writes, no Contract Vehicle Watch.

This checklist is the **source-acquisition** follow-on to the RSS feed expansion (PR #37) and the strategy docs ([`wild_opportunity_discovery_strategy.md`](wild_opportunity_discovery_strategy.md), [`research/opportunity_expansion_plan_2026-06.md`](research/opportunity_expansion_plan_2026-06.md)). Most remaining high-value sources are **registration / commodity-alert** setups, not code. The goal: register once with the right commodity terms so each portal *emails* matching opportunities, then forward those emails into the existing ingest funnel.

> **The one rule that makes this work — forward every portal alert into the funnel.**
> Set each portal's notification address to the business mailbox and forward those alerts into the Gmail/Graph funnel already documented in [`email_ingest_setup.md`](email_ingest_setup.md). `tools/ingest_email.py` already **unwraps forwarded Outlook alerts** (recovers the original portal sender/subject) and routes them through `relevance.py`, so a forwarded alert is processed exactly like a direct one. Nothing else is needed for an alert to reach the pipeline.

> **URL/verification legend** (per `sources/README.md` URL-caution rule):
> **[committed]** = URL already in `sources/procurement_sources.json` (authoritative). **[verified-research]** = fetched live during June 2026 research. **[UNVERIFIED]** = real entity, exact registration URL not yet confirmed — **confirm before relying**; use the portal's own search rather than a guessed deep link.

> **Routing reminder.** Explicit mattress / product-fit solicitations → **Active pipeline** (`relevance.ACCEPT`). Broad furniture / FF&E / co-op vehicles / buyer-intel → **Lead Radar** (`relevance.REVIEW`). The classifier decides automatically; the "usual route" column below is just what to expect from each channel.

---

## Master commodity / search-term list

Select as many of these as each portal's commodity taxonomy allows (NIGP class, free-text saved search, or category checkboxes). Paste the free-text set into keyword/saved-search fields.

```
mattress, mattresses, bedding, box spring, bed frame, beds, bunk,
dormitory furniture, residence hall, student housing, Twin XL,
institutional furniture, FF&E, furniture and related services,
correctional supplies, inmate supplies, jail mattress, detention bedding,
shelter supplies, emergency supplies, cots, public health bedding,
residential care furniture
```

**Commodity codes where portals filter by code** (select alongside the keywords):
- **NIGP:** `205` Bedding/Linens/Mattresses (incl. `205-49` mattresses, `205-55` pillows); `420` Furniture: Dormitory/Household (`420-15` beds/headboards, `420-26` dormitory furniture). *(`425` Office furniture is SOFT — expect Lead Radar.)*
- **NAICS:** `337910` Mattress Mfg; `337127` Institutional Furniture.
- **PSC (SAM/federal):** `7210` Household Furnishings; `7105` Household Furniture.

> Tip: register the **same** commodity selections on every portal so coverage is consistent. On portals that only allow a few categories, prioritize NIGP `205` (mattresses/bedding) and `420` (dormitory furniture).

---

## Priority 1 — Direct / high-value mattress channels

The highest-conviction, most-direct mattress demand. Set these up first.

### 1.1 BuyBoard (TX Local Government Purchasing Cooperative)
- **URL:** https://www.buyboard.com/ [committed] · Vendor registration runs on IonWave: `buyboard.ionwave.net/VendorRegistration` [verified-research]
- **Why it matters:** Largest TX local-gov co-op; contract **#767 "Furniture for School, Office… and Dormitory"** explicitly names dormitory furniture — the single best dorm-furniture vehicle. Becoming an awarded vendor means being invited to buys that never post publicly.
- **Commodity/profile terms:** mattress, mattresses, dormitory furniture, residence hall, Twin XL, bed frame, beds, bunk, institutional furniture, FF&E, furniture and related services (NIGP 205, 420).
- **Alert frequency:** Per-solicitation invitations (IonWave commodity-code alerts); not a digest cadence.
- **Email/forwarding:** Set notification email to the business mailbox; forward to the funnel.
- **Usual route:** **Lead Radar** (broad furniture vehicle / `co-op_contract_vehicle`); an explicit mattress line within a solicitation → Active.
- **Human follow-up:** **Yes — vendor application.** Next furniture re-bid ~2028, so register now to be positioned/alerted. Track the re-bid window.

### 1.2 TDCJ / Texas SmartBuy (ESBD) / Texas CMBL
- **URLs:** TDCJ Bonfire `tdcj.bonfirehub.com` [verified-research, already an RSS feed in `configs/feeds.json`] · Texas SmartBuy / ESBD https://www.txsmartbuy.gov/esbd [committed] · Texas CMBL https://comptroller.texas.gov/purchasing/vendor/cmbl/ [committed]
- **Why it matters:** TDCJ is the largest US state prison system — mattresses are a continual consumable. ESBD is the single highest-leverage TX **state-agency** board (TDCJ, TJJD, HHSC state hospitals, TDEM, state residential schools all post there). CMBL commodity-code selections drive Texas agency notifications.
- **Commodity/profile terms:** mattress, mattresses, bedding, box spring, jail mattress, detention bedding, correctional supplies, inmate supplies, institutional furniture, cots, shelter/emergency supplies. **Maintain CMBL NIGP codes 205 + 420** so agency notifications fire.
- **Alert frequency:** ESBD — set up saved searches (review weekly); CMBL — automatic agency notifications by commodity code; TDCJ Bonfire — already ingested via RSS.
- **Email/forwarding:** CMBL/ESBD notifications → business mailbox → funnel.
- **Usual route:** **Active** for explicit mattress/bedding/correctional-mattress solicitations; **Lead Radar** for broad furniture/FF&E.
- **Human follow-up:** **Confirm CMBL commodity-code selections are current** (205/420 + correctional/medical/dormitory). Note: TX state-agency mattress volume is partly absorbed by the **TCI/WorkQuest set-aside** — verify how supplemental purchases are allowed.

### 1.3 Texas A&M — AggieBid / SciQuest
- **URL:** Texas A&M University System procurement https://www.tamus.edu/procurement/ [committed] · AggieBid public board https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=TAMU [verified-research] · AggieBuy/AggieBid supplier portal https://solutions.sciquest.com/apps/Router/SupplierLogin?CustOrg=TAMU [verified-research]
- **Why it matters:** ~11,000+ on-campus beds plus the Corps of Cadets — one of the largest standing dorm inventories in the region, on a summer refresh cycle.
- **Commodity/profile terms:** residence hall, student housing, Twin XL, dormitory furniture, mattress, mattresses, bed frame, beds, bunk, FF&E, furniture and related services.
- **Alert frequency:** Vendor-portal notifications by category (configure on registration); else monitor the public bid board.
- **Email/forwarding:** Portal notifications → business mailbox → funnel.
- **Usual route:** **Lead Radar** for residence-hall FF&E; **Active** for an explicit mattress/Twin-XL solicitation.
- **Human follow-up:** **Register in AggieBuy/AggieBid** and select mattress/dormitory/residence-hall/furniture terms or commodity codes where available; forward alerts to the funnel. Public sweep 2026-06-21 found 19 open events but no current mattress, bedding, dormitory, bed, Twin XL, or furniture product-fit opportunity.

### 1.4 Region ESC / EPIC / IonWave-style furniture co-ops (esp. Region 4 ESC → OMNIA)
- **URL:** Region 4 ESC supplier portal `region4esc.ionwave.net` [verified-research]
- **Why it matters:** Region 4 ESC (Houston) is the **lead agency for OMNIA Partners** and the largest TX purchasing co-op — it awards statewide furniture / dorm / FF&E contracts, and OMNIA's furniture catalog already includes a **named mattress incumbent (Gateway Mattress)**, proving the category exists. (Note: the EPIC6 / ESC Region 6 eMarketplace is the IonWave instance that produced the broad-furniture leads already in Lead Radar.)
- **Commodity/profile terms:** mattress, mattresses, dormitory furniture, residence hall, student housing, institutional furniture, FF&E, furniture and related services, bed frame, beds, bunk (NIGP 205, 420).
- **Alert frequency:** IonWave commodity-code email alerts (per matching solicitation).
- **Email/forwarding:** Register business mailbox; forward IonWave alerts to the funnel (already unwrapped by `ingest_email.py`).
- **Usual route:** **Lead Radar** (`co-op_contract_vehicle` / broad furniture); explicit mattress solicitation → Active.
- **Human follow-up:** **Register on Region 4 ESC IonWave with NIGP 205/420.** Watch for the next furniture / student-housing RFP (gateway to OMNIA).

---

## Priority 2 — State portals across the service geography

One registration per state board unlocks statewide-agency alerts (corrections, universities, state hospitals, emergency management). Register the business mailbox + commodity codes on each.

| Portal | URL | Why | Terms / codes | Alerts | Route |
|---|---|---|---|---|---|
| **Oklahoma OMES Supplier Portal** | https://oklahoma.gov/omes/divisions/central-purchasing/solicitations.html [committed] | OK state agencies incl. **ODOC** (corrections) and OK Office of Juvenile Affairs; OK universities | mattress, bedding, correctional/inmate supplies, dormitory furniture, FF&E; NIGP 205/420 | Supplier-portal email notifications by commodity | Active (mattress) / Lead Radar (furniture) |
| **Louisiana LaPAC / LaGov** | https://wwwcfprd.doa.louisiana.gov/osp/lapac/pubmain.cfm [committed] | LA DPS&C (corrections), LSU + UL System dorms, LA state hospitals; **named in-state mattress incumbent (Grand Bedding)** + dorm furniture (Norix) on state contract | mattress, bedding, dormitory furniture, residence hall, correctional supplies, FF&E | LaGov supplier self-registration → RFx email notifications | Active (mattress) / Lead Radar (furniture) |
| **Mississippi MAGIC / DFA** | https://www.dfa.ms.gov/mississippi-suppliersvendors [committed] · supplier self-service `dfa.ms.gov/supplier-self-service` [verified-research] | **"Furniture–Cafeteria/Dormitory" statewide contract is multi-vendor, names dorm + mattress categories, and out-of-state vendors already win** — the most winnable near-term award; plus MDOC corrections | mattress, mattresses, dormitory furniture, residence hall, bedding, FF&E, institutional furniture | MAGIC Supplier Self-Service (SUS) RFx notifications by category | **Active/Lead Radar** — and **bid the FY26-27 furniture solicitation** |
| **Arkansas ARBuy** | https://arbuy.arkansas.gov/ [committed] | AR Division of Correction, U of Arkansas + Arkansas State dorms; state contract built on TIPS/OMNIA | mattress, bedding, dormitory furniture, correctional/inmate supplies, FF&E | ARBuy vendor notifications by category | Active (mattress) / Lead Radar (furniture) |
| **New Mexico GSD / Bonfire** | https://generalservices.state.nm.us/state-purchasing/ [committed] · NM is migrating to **Euna/Bonfire** `generalservices-state-nm-us.bonfirehub.com` [verified-research] | NM Corrections, UNM/NMSU dorms; NM mid-transition off SciQuest to Bonfire by ~summer 2026 | mattress, bedding, dormitory furniture, residence hall, FF&E; NIGP 205/420 | Register on the **current** NM portal (confirm Bonfire vs legacy) for email alerts | Active (mattress) / Lead Radar (furniture) |

- **Email/forwarding (all P2):** set the business mailbox as the notification address; forward to the funnel.
- **Human follow-up (all P2):** **register/refresh commodity profile on each** (NIGP 205/420 + correctional/dormitory). For **NM**, confirm whether the live portal is Bonfire or the legacy GSD page before registering. For **MS**, the registration is also the gateway to bidding the dormitory furniture contract — flag for proposal work.

---

## Priority 3 — Co-op / furniture vehicle monitoring

These are **vehicle** plays: register to become an awarded vendor and/or monitor for re-solicitation. Most alerts here are broad furniture → **Lead Radar** (`co-op_contract_vehicle`); the value is catching the next furniture/FF&E RFP and getting on contract.

| Co-op | URL | Why / status | Terms | Alerts | Route | Follow-up |
|---|---|---|---|---|---|---|
| **TIPS** | https://www.tips-usa.com/ [committed] · vendor `tips-usa.com/vendors/become`, bids on `tips.ionwave.net` [verified-research] | Furniture re-solicited **~yearly** = shortest wait to bid | dormitory furniture, residence hall, mattress, FF&E, furniture and related services | Monthly bid notices + IonWave commodity alerts | Lead Radar | **Apply** — respond to next "Furniture, Furnishings & Services" RFP |
| **Choice Partners (HCDE)** | https://www.choicepartners.org/ [committed] · register `hcdeebid.ionwave.net/VendorRegistration.aspx` [verified-research] | Local Houston; next **Furniture, Fixtures, Equipment (FFE) and Related Items** advertise estimate 2027-06-01; **no dorm/mattress line yet** | FF&E, institutional furniture, bed frame, dormitory furniture | IonWave commodity alerts | Lead Radar | **Register**; good for bed frames/FF&E and watch the 2027 FFE cycle |
| **Sourcewell** | https://www.sourcewell-mn.gov/ [committed] · procurement portal `proportal.sourcewell-mn.gov` [verified-research] | Furniture Solutions contract family `091423` matures 2027-12-04; KI page explicitly includes dormitory/library furniture; no current mattress line | dormitory furniture, residence hall, mattress, FF&E | Procurement-portal category alerts | Lead Radar | **Register for alerts**; monitor the 2027 furniture re-bid window |
| **E&I Cooperative Services** | https://www.eandi.org/ [committed] · supplier/RFP path via SciQuest `CustomerOrg=EandICooperative` [verified-research] | Higher-ed cooperative; active University Sleep Products residence-hall mattress contract runs through 2031-01-31 | mattress, residence hall, dormitory furniture, student residential furniture, bedding | SciQuest supplier/RFP alerts | Lead Radar | **Register for alerts**; monitor the next RFP 683486 mattress cycle |
| **OMNIA Partners** | https://www.omniapartners.com/ [committed] · register via Region 4 ESC IonWave (see §1.4) | Largest national co-op; **mattress category proven** (Gateway Mattress); local TX lead agency | mattress, dormitory furniture, residence hall, FF&E | Via Region 4 IonWave commodity alerts | Lead Radar | **Apply via Region 4 ESC** (highest reward) |
| **HGACBuy** | https://www.hgacbuy.org/ [committed] · `hgacbuy.org/join/become-a-contractor` [verified-research] | **No furniture/FF&E/mattress category exists** (verified) | n/a | n/a | n/a | **Skip / monitor only** — optionally petition for a new FF&E category |

> **Net-new vehicles worth registering** (from research, optional but high-value): **Equalis Group** (`equalisgroup.org` [verified-research] — furniture with **no entrenched mattress incumbent = white space**, TX lead agency Region 10 ESC). **E&I Cooperative Services** has now been promoted into the P3 table because it has public higher-ed interiors coverage and a named University Sleep Products mattress incumbent. Route: Lead Radar.

> **Cross-state leverage:** a single national co-op award (OMNIA / TIPS / Equalis / Sourcewell) grants pass-through buying eligibility in **all six states** — the cheapest way to reach OK/LA/MS/AR/NM beyond the state boards.

---

## Priority 4 — University / county / local portals

Lower volume individually but high standing bed counts and new-construction FF&E buys. Register or monitor where a portal exists; close UNVERIFIED URL gaps before relying.

### Universities (residence-life / dorms)
| Buyer | Procurement page | Why | Route |
|---|---|---|---|
| University of Oklahoma (OU) | `ou.edu/purchasing` [UNVERIFIED] | New South/North residence halls under construction = new bed buys | Lead Radar / Active (mattress) |
| Oklahoma State (OSU) | `adminfinance.okstate.edu/purchasing/` [UNVERIFIED] | Large Stillwater residential system | Lead Radar / Active |
| LSU | `lsu.edu/procurement/` [UNVERIFIED] (posts via LaPAC) | New residence halls broke ground Dec 2025 = imminent FF&E | Lead Radar / Active |
| Ole Miss | `procurement.olemiss.edu` [UNVERIFIED] | Large hall system | Lead Radar / Active |
| Mississippi State | `procurement.msstate.edu` [UNVERIFIED] (also Bonfire: MS IHL feed) | Large Starkville base | Lead Radar / Active |
| University of Arkansas | `procurement.uark.edu` [UNVERIFIED] | Pomfret ~800 + large system | Lead Radar / Active |
| UNM | `purchasing.unm.edu` [UNVERIFIED] | Coronado + halls, Albuquerque | Lead Radar / Active |
| NMSU | SciQuest `bids.sciquest.com/.../PublicEvent?CustomerOrg=NMSU` [verified-research] | ~3,269 beds; new Juniper hall | Lead Radar / Active |

- **Terms:** residence hall, student housing, Twin XL, dormitory furniture, mattress, bed frame, beds, bunk, FF&E.
- **Alerts/forwarding:** register on each vendor portal for category notifications → forward to funnel; several MS public universities are already covered by the **Bonfire: Mississippi IHL** RSS feed (no action needed there).
- **Human follow-up:** **confirm each procurement/bids URL** (most are UNVERIFIED) and register; prioritize buyers with active hall construction (LSU, OU).

### County / jail-related & local
| Buyer | Portal | Why | Route |
|---|---|---|---|
| Dallas County / Sheriff (jail ~7,100 beds) | BidNet `bidnetdirect.com/texas/dallas-county` [verified-research] | One of the largest US jails; high mattress turnover | Active / Lead Radar |
| Bexar County / ADC (San Antonio, 4,000+ beds) | Bexar County Purchasing [UNVERIFIED] | Large jail; recurring replacement | Active |
| Bernalillo County (Albuquerque) / MDC | Bernalillo County Purchasing [UNVERIFIED] | Largest NM metro jail; NM coverage | Active |
| (also) Walker County, TX | Bonfire `co-walker-tx.bonfirehub.com` [verified-research; RSS configured] | Huntsville (TDCJ HQ); jail/institutional bedding | Active / Lead Radar |
| (also) BidNet Direct — TX, LA & OK Groups | `bidnetdirect.com/texas`, `/louisiana`, `/oklahoma` [verified-research; TX+LA registered] | One registration aggregates many local agencies; TX page showed 2,302 statewide/federal open solicitations + 78 group bids on 2026-06-21; profile has NIGP 42068 | Active / Lead Radar |

- **Terms:** jail mattress, detention bedding, correctional supplies, inmate supplies, mattress, bedding, cots.
- **Alerts/forwarding:** register for commodity notifications (DemandStar/BidNet support free commodity alerts) → forward to funnel.
- **Human follow-up:** **confirm county jail procurement portals** (mostly UNVERIFIED — many run on IonWave/Euna); use registered **BidNet TX + LA groups**, add/verify **BidNet OK**, and use **DemandStar** as efficient aggregators. BidNet keyword result pages require/blocked to automated public fetches, so run the mattress/bedding/dormitory/correctional saved searches after login.

---

## Setup summary & follow-up

**Do in this order:**
1. **P1 first** — BuyBoard, TDCJ/ESBD/CMBL commodity profile, Texas A&M AggieBid, Region 4 ESC IonWave.
2. **P2** — register/refresh the five state boards (OMES, LaPAC, MAGIC, ARBuy, NM) with NIGP 205/420; bid the MS dormitory contract.
3. **P3** — apply to TIPS + OMNIA (via Region 4), register Sourcewell/Choice Partners/Equalis/E&I for alerts; skip HGACBuy.
4. **P4** — confirm UNVERIFIED university/county URLs, register, and lean on BidNet/DemandStar aggregators.

**For every portal:** set the **business mailbox** as the notification address and **forward the alerts into the Gmail/Graph funnel** in [`email_ingest_setup.md`](email_ingest_setup.md). `tools/ingest_email.py` unwraps the forwarded alert and routes it via `relevance.py` — **ACCEPT → active pipeline, REVIEW → Lead Radar** — with no further code needed.

**Open verification debt** (confirm before relying): NM live portal (Bonfire vs legacy GSD); university procurement pages (OU/OSU/LSU/Ole Miss/Miss State/UArk/UNM); county jail portals (Dallas/Bexar/Bernalillo); current expirations on OMNIA Gateway Mattress and LA Norix contracts.

---

### Scope note
This document is an operator runbook only. No code, `configs/feeds.json`, CSV, parser-adapter, or Contract Vehicle Watch changes were made. URLs are cited from the committed source registry or flagged by verification status; nothing was invented.
