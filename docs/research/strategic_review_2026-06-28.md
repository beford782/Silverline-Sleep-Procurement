# Strategic Review — The Mattress Opportunity Funnel at 50,000 ft

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-28
- **Method:** 5 parallel analyst agents (demand-universe coverage · private-sector funnel design ·
  funnel mechanics/recall · win-engine/conversion · skeptical strategy), each grounded in the actual
  repo (code, ledger, Lead Radar, archive, audit), then synthesized.
- **The question:** the tool's true purpose is a funnel for the **BEST and ALL** mattress opportunities,
  **public AND private**. How well does it serve that, and how else could it be improved?

---

## The verdict (one paragraph)

You've built a clean, well-maintained machine for catching the **lowest-value, latest-stage,
least-winnable slice** of institutional mattress demand — publicly-posted government RFPs — and have
been measuring success by how *tidy* it stays rather than revenue produced. The funnel is the right
**monitoring layer** and the wrong **primary growth engine**. The true mandate is half-unbuilt: the
entire **private sector has no intake at all**, and the highest-revenue levers (co-op/GPO **contract
awards**, the **Restonic/Spring Air licensor channel**, and **spec-position before the RFP**) are barely
touched. The fix isn't more sources — it's **repointing** the system at the 90% of the market it
currently can't see.

## What the data proves (not opinion — the repo's own records)

- **Zero funnel wins.** The only "win" in `bids/archive/` (City of Austin IFB 8300, ~$58k) **predates
  the tool**. Everything the funnel has surfaced is a no-bid.
- **Every surfaced bid failed for a structural reason** — read the no-bid archive as a diagnosis:
  *too late* (past-due/same-day at ingest), *wrong product* (Purple-brand required, bariatric medical,
  protectors-only, litter pads, aircraft, furniture sets with one mattress CLIN), *wrong geography*
  (MD, ND, MN, CO, **Italy** — mattresses are bulky low-density freight; out-of-region loses), or
  *can't transact* (SAM not Active).
- **The highest-fit leads were tombstones.** LaPAC statewide Mattresses (fit 95), Bernalillo
  Correctional Mattresses (90), E&I residence-hall mattress (90) — all **closed or awarded to multi-year
  incumbents** (Grand Bedding, Gateway, University Sleep) before the sweep saw them.
- **The real pattern:** winnable mattress contracts exist **on a multi-year cycle**; the funnel reliably
  **arrives after the award**. The remaining ~45 Lead Radar rows are broad furniture co-op vehicles
  whose re-bid windows are **2027–2031** — and each "reminder" is a dead string in a notes cell.

The active pipeline being *empty* has been celebrated as discipline. It is more honestly a
**demand-generation gap wearing a clean shirt.**

---

## The four revenue levers the tool barely touches (ranked)

1. **Co-op / GPO CONTRACT AWARDS — the actual economic engine.** Winning a co-op/state-term mattress or
   FF&E award produces **years of member pull-through without per-bid hunting**. Your own strategy doc
   calls this "the single biggest lever," then operationalizes it as "register and wait for 2028." That's
   subscribing, not pursuing.
2. **The Restonic / Spring Air LICENSOR channel — a total blind spot.** As a licensee you have rights to
   the licensors' national-account and **hospitality/contract** programs, the GPO relationships they
   already hold, and territory-routed leads. It appears **nowhere** in the repo. Free, warm,
   territory-protected demand you already own — while the tool mines public RSS.
3. **The PRIVATE sector — unbuilt, not under-covered.** Every source, feed, and lead row is a government
   channel. Hospitality, senior living/LTC, private hospitals, student-housing REITs, privatized military
   housing, and **private corrections** have **no intake mechanism**. These have larger aggregate demand,
   **margins not capped by low-bid mandates**, and recurring replacement cycles.
4. **Spec-position BEFORE the RFP.** Demand is often knowable 12–24 months out (e.g., TX HHSC's
   **published** state-hospital bed-expansion forecast). You win by being **specified early**; you lose by
   catching the RFP when it posts, already written around the incumbent.

### The biggest uncovered private segments (from the coverage map)
- **Hotels & hospitality + PIP/renovation cycles** — best natural fit (your Restonic/Spring Air licenses
  include hospitality lines); reached via brand-standard programs, hotel mgmt cos, and FF&E procurement
  firms (Benjamin West, HVS Design).
- **Senior living / LTC / SNF + healthcare GPOs** — recurring fluid-proof demand via **Direct Supply /
  DSSI**, Value First, and Vizient/Premier/HealthTrust (your own audit flagged GPOs as "deferred").
- **Private corrections — CoreCivic, GEO Group, MTC, and in-region LaSalle (TX/LA).** A glaring asymmetry:
  the funnel registers with a dozen public jails and six state DOCs but misses the largest private
  operators with the *identical* continual-replacement product.
- **3rd-party student-housing operators / REITs** — Greystar, American Campus, Scion, Landmark, Core
  Spaces — now run a large, growing share of beds, all off-portal.
- **Privatized military family/barracks housing** — Lincoln, Balfour Beatty, Hunt, Corvias — high-value,
  mattress-heavy, and **not blocked by the SAM/UEI problem** (they buy FF&E directly).

---

## What to STOP

- **Stop growing portal/RSS count as the core activity.** ~20 registrations already cover your region;
  the 21st adds ~zero. The audit's 92 findings are mostly plumbing-on-plumbing.
- **Stop the entity-correction documentation sprawl.** The live-portal sweep proved the fix is tiny (the
  W-9/EIN was always correct). Execute the **one** SAM LLC validation (or FSD ticket), close it, move on.
- **Stop chasing out-of-region / federal SAM bids.** They lose on freight + set-asides + late timing even
  when SAM is Active. Keep a saved search; only treat federal as a lane with an **in-region** target
  (Tinker, Ft. Cavazos, JBSA/Lackland) where freight works.
- **Stop polishing the relevance classifier.** It's adequate; processing quality was never the constraint.

---

## What to BUILD — the repoint (three workstreams)

### A. Demand side — build the PRIVATE funnel (the missing half)
The public logic ("add sources/feeds") **does not extend to private** — there are no portals to scrape.
The architectural unlock is a **second intake motion** that reuses the pipeline you already have:
- **"Demand Radar" + a demand-signal classifier lane.** `relevance.py` only understands *procurement*
  language. Add a parallel lane for **demand-signal vocabulary** — *breaks ground · tops out · now leasing ·
  opens 2027 · 180-key hotel · PIP/re-flag · +200 beds* — landing in a new `_demand_radar.csv` keyed by
  **estimated buy-window date** (not bid-due), each requiring human outbound. Same RSS/email plumbing.
- **Google Alerts → RSS** (the pipeline already unwraps Google redirects — it was *built* for this; none
  are configured). Metro-cloned alerts on hotel/senior-living/student-housing/jail construction + PIP +
  trade-press RSS (Hotel Business, Senior Housing News, Student Housing Business, Correctional News).
  Zero cost.
- **Construction-data alerts → email channel.** One paid subscription (ConstructConnect, or **BuildCentral
  HotelInventory + MedInventory**, or **STR/Lodging Econometrics** hotel pipeline) scoped to your six
  states, digest routed to the inbox the funnel already reads → 12–18-month-ahead leads with bed/key
  counts + owner/GC contacts.
- **GPO / distributor enrollment** (where private demand pools): **Direct Supply/DSSI** (senior living),
  **Guest Supply / HD Supply / Hilton Supply Mgmt / Avendra** (hospitality), **AAHOA** membership,
  Value First / Vizient / Premier (healthcare — slow-burn).
- **Municipal building-permit open-data adapter** (build-once): Houston/Dallas/Austin/San Antonio publish
  permits via Socrata/ArcGIS JSON — filter new-construction by occupancy type → earliest free signal.

### B. Win side — make it a Win Engine, not a bid-catcher
- **Win Score replaces binary `fit_score`.** `win_score = product_fit × value_tier × win_probability ×
  strategic_fit`. Keep `relevance.confidence` as the product-fit *input*. Backfill the blank
  `estimated_value` from bed-counts already in the docs. Result: the digest surfaces the few you can
  **win**, and auto-demotes the Norix/closed-incumbent noise that currently ranks like a live fit.
- **A re-bid calendar that FIRES.** Turn the 2027–2031 windows from dead notes into **Google Calendar
  events** keyed to `expiry − prep_lead_time` (~6 mo co-ops), each with a prep checklist (confirm spec →
  pull last award price/incumbent → register → buyer touch). Google Calendar tooling is available in this
  environment.
- **Incumbent / award intelligence as structured fields** (`incumbent`, `award_price`, `award_date`,
  `spec_summary`) — the data is public (Bonfire `IsPublicAward`, LaPAC PDFs) and already sitting in
  free-text. Arms both win-probability and pricing for the next cycle.
- **A readiness / eligibility ledger** — make the inert `gate_status`/`compliance_blocker` columns
  load-bearing. A company capability matrix (SAM Active, 16 CFR 1633, CAL/TB 117, FR/fluid-proof covers,
  GPO eligibility, bonding) maps to each lead, and `workflow_check.py` ERRORs on biddable-but-blocked.
  Produces a ranked "fix this to unlock the most pipeline" list — today that's **SAM** (unblocks 3
  recurring federal channels at once).
- **A one-page capability sheet** ("what we make / what we don't") to filter the **capability-mismatch
  no-bids** (Purple, bariatric, protectors-only, aircraft) at the source and redirect targeting to
  winnable specs.
- **Light buyer CRM** — structure the buyer contacts already scattered in notes (re-buy cadence, next
  window) so relationship pre-work and re-buy anticipation actually happen.

### C. Reliability — only the silent-miss critical few (NOT all 92 audit items)
The federal channel + relevance engine are already solid (audit do-now items shipped). The remaining
holes that matter:
- **RSS fetch-failures are still swallowed** — `ingest_rss` catches every feed error and exits 0. A
  Bonfire 403 or dead feed = zero rows, green run, no alert. **This is the channel that carries
  Bernalillo-class county correctional RFBs — fix #1:** count fetched-vs-failed and exit non-zero on
  failure so the existing alert fires.
- **The digest is blind to the live email channel** — `procurement_digest.yml` filters for a workflow
  name that no longer exists, so the daily IMAP ingest (your primary state/local channel) never shows in
  the health view. One-line fix.
- **No reject-log audit trail** — you can't see *misses* without logging REJECTs; wire `--reject-log`
  everywhere (and add it to `ingest_sam`).
- **SAM 429 throttle looks identical to an empty week** — add bounded retry + a distinct "throttled" signal.
These four make "no news = genuinely no opportunities" a statement you can trust. Skip the rest of the
audit backlog for now.

---

## 90-day plan — top 3 moves (do these first)

1. **Open the Restonic / Spring Air licensor channel — week 1, no code.** Call the licensors'
   contract/hospitality national-account divisions; get named as the institutional/hospitality referral
   for TX/OK/LA/MS/AR/NM and onto their lead distribution. Highest ROI, lowest cost, completely untapped.
2. **Convert co-ops from "watch" to "bid the open windows now."** Stop waiting for 2028. Bid the
   **Mississippi DFA "Furniture–Cafeteria/Dormitory"** term contract (annual, explicit mattress line,
   out-of-state vendors already win), pursue **Equalis** (furniture category with *no* entrenched mattress
   incumbent = white space) and **TIPS**. **One national co-op award = pull-through across all six states.**
3. **Build a top-20 regional buyer account plan + finish SAM as a contained task.** For TDCJ, TX HHSC
   state hospitals (published expansion), Texas A&M/Texas State, and the big county jails: capture
   replacement cycle, construction timeline, incumbent, and contracting contact → **direct outreach to get
   specified before the RFP.** In parallel, do the SAM LLC validation **once** and add the capability sheet.

*Alongside (small PRs): stand up the **private Demand Radar** pilot (Google Alerts→RSS + demand lane) and
the **Win Score** so the funnel ranks winnability and starts sensing private demand.*

## 12-month shape
- **Q1:** Licensor channel opened · open co-op bids submitted (MS DFA, Equalis, TIPS) · SAM/entity fully
  resolved · top-20 account plan live · capability sheet gating the funnel.
- **Q2–Q3:** Land **1–2 co-op/state-term awards** (the pull-through engine) · launch a **private-sector
  pilot** (regional hospitality + senior living via the licensor program) · get **specified into 2–3
  new-construction projects** ahead of their RFPs.
- **Q4:** Re-baseline on revenue KPIs · the funnel **demotes to a background monitoring layer feeding the
  account plan**, not the growth engine.

## The KPI shift (this is the real change)
| Stop measuring | Start measuring |
|---|---|
| bids ingested, registrations complete, pipeline cleanliness | co-op/term **awards held** · member **pull-through $** · qualified **private-sector** opps · **specs influenced** pre-RFP · **in-region bids won** |

---

### Caveat
Specific third-party services, GPOs, distributors, associations, and operator names above are from the
agents' general knowledge, **not** freshly verified — confirm current names, RSS/alert availability, and
supplier-onboarding fit before committing spend. The two zero-cost in-house first moves (licensor call;
Google Alerts→RSS + demand lane) carry no such risk and should go first.
