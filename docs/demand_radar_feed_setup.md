# Demand Radar — Feed Setup & Triage Runbook (turn the private funnel ON)

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-28 · **Reframed:** 2026-06-29
- **STATUS (2026-06-30): the pilot is LIVE.** All **7 feeds are created and wired** into
  `configs/feeds.json` as `kind:"demand"` (PR #96, merged to main). The Mon/Thu ingest now reads them;
  **0 demand rows captured so far** (feeds fill as Google finds matches). The feed-creation steps below are
  retained as **reference** (for re-creating a feed, or adding Pilot C / new geos later). The live work now
  is **§2 — triage each real hit by hand.**
- **What:** The Demand Radar engine is built and merged (`tools/demand_signal.py`, `tools/demand_radar.py`,
  `kind:"demand"` routing in `ingest_rss.py`, digest/email surfacing), now fed by 7 Google Alerts RSS feeds.
  This runbook was the one-time operator setup to feed it — mostly **creating Google Alerts as RSS**, which
  only you can do (Google's Alert RSS URLs are generated in the Alerts UI; they can't be hand-built).
- **How it flows once set up:** each feed → `ingest_rss.py` (demand lane) → `demand_signal.classify_demand`
  → `leads/demand/_demand_radar.csv` (keyed by estimated buy-window) → your digest/email "Demand Radar"
  section → **you triage the route-to-market** → you/sales do outreach
  (`python tools/demand_radar.py outreach <id> --contact ...`).

---

## 0. What Demand Radar IS (and is NOT) — read this first

> **Demand Radar is not a lead list. A demand signal is not an open buy.** Each signal must be triaged for
> **route-to-market before any outreach.** Branded hotels and national senior-living / hospital chains are
> usually **channel** opportunities (brand standard, GPO, FF&E firm, approved-vendor program), **not**
> direct-local leads — for those the value is *account mapping*, not cold-selling the property. The pilot
> prioritizes high-signal events where a *plausible route can be mapped*: hotel **PIP / re-flag**,
> **independent / regional** hospitality, and **shelter / workforce / crew** housing. **Restonic / Spring Air
> may be tagged as a possible route class, but that licensor channel is operator-owned (Blake handles it
> internally) and is NOT worked by the assistant** — it is a classification label only.

Purpose, stated precisely: **"Find private mattress demand events and map the route-to-market before the buy
is locked"** — not "find private mattress buyers." A construction article is *demand intelligence*; the job
is to identify whether — and how — we could plausibly win, and to **kill the unwinnable ones early.**

This reframe is the documented strategy made operational — `docs/research/strategic_review_2026-06-28.md`
already calls for spec-positioning *before* the RFP, private-demand visibility, channel/GPO pull-through, and
measuring *specs-influenced / private opps* instead of "pipeline tidiness." This runbook just makes the
Demand Radar's triage match that.

---

## 1. The pilot — start SMALL (7 feeds), prove signal, then expand

Don't start with broad alerts. Start with **two purpose-driven pilots, 7 feeds total**, all **Texas-first**
(home market, where the buying networks concentrate). Review real hits before adding Pilot C or new geos.

**For each feed:** go to **google.com/alerts**, paste the query, **Show options** → **Deliver to = RSS feed**,
**Sources = Automatic**, **How many = All results**, **Create Alert**, then on the manage page click the
**orange RSS icon** and copy the feed URL. Google honors quoted phrases and caps `OR`.

### PILOT A — Hotel PIP / Re-flag / Renovation  (account mapping) — **5 feeds, create first**
*Highest-value, recurring mattress signal (4–12 mo PO window). Purpose: surface OWNERS/operators doing
renovations → map the buying network (owner, mgmt co, FF&E firm, brand timeline, repeat PIP across a
portfolio). Most will be `channel`/`spec-position`, not direct sells — that's expected.*

```
("property improvement plan" OR "re-flag" OR reflag OR rebrand OR "brand conversion" OR "hotel conversion" OR "guestroom renovation" OR "soft goods" OR "soft-goods" OR "case goods") (hotel OR hospitality OR "extended stay" OR "extended-stay") (rooms OR keys OR guestrooms OR "guest rooms") <LOC>
```
Clone across `<LOC>` = `Houston` · `("Dallas" OR "Fort Worth")` · `Austin` · `"San Antonio"` · `Texas` (statewide).

> **Already tightened (2026-06-29):** bare `PIP`, generic `renovation`, and bare `conversion` were removed to
> cut noise — only the specific phrases stay (`"property improvement plan"`, `"brand conversion"`,
> `"hotel conversion"`, `"guestroom renovation"`, plus re-flag / rebrand / soft-goods / case-goods). Do **not**
> re-add the bare tokens. If a feed still floods, narrow the geo — don't broaden the triggers.

### PILOT B — Independent / Regional Hospitality  (direct-sale test) — **2 feeds**
*Less brand-locked → more direct-sale potential. Misses some opps but what it finds is less channel-locked.*

```
("boutique hotel" OR "independent hotel" OR "locally owned hotel" OR "locally-owned hotel" OR "family owned hotel" OR "extended stay hotel" OR "extended-stay hotel") ("renovation" OR "rebrand" OR "set to open" OR "under construction" OR "breaks ground") (rooms OR keys OR guestrooms OR "guest rooms") <LOC>
```
Clone across `<LOC>` = `Texas` (statewide) · `Houston`.  *(Swap Houston → `("Dallas" OR "Fort Worth")` if you prefer.)*

### The 7 starting feeds + `feeds.json` labels  ✅ LIVE (wired 2026-06-30, PR #96)
These 7 are already in `configs/feeds.json`. Kept here as the canonical label list (for re-creating a feed
or matching a row's `source` back to its pilot/geo):
```json
{ "source": "Demand Radar: Pilot A PIP-Reflag Houston",      "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot A PIP-Reflag Dallas-FW",    "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot A PIP-Reflag Austin",       "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot A PIP-Reflag San Antonio",  "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot A PIP-Reflag Texas",        "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot B Independent Texas",       "url": "<RSS>", "kind": "demand" },
{ "source": "Demand Radar: Pilot B Independent Houston",     "url": "<RSS>", "kind": "demand" }
```
Keep the `Demand Radar: ` prefix and `Pilot A/B/C` slug exactly (the digest groups on them). Existing
procurement feeds need no change (absent `kind` defaults to `procurement`).

### PILOT C — Shelters / Workforce / Crew Housing  — **HOLD until the first batch is reviewed**
*Likely the most directly actionable (least brand/GPO lock-in, fast 1–9 mo cycles), but add it after Pilot A/B
prove out. When you do, start with ONE statewide-Texas alert (these items are sparse + the broad terms are
noisy):*
```
("homeless shelter" OR "navigation center" OR "transitional housing" OR "workforce housing" OR "crew housing" OR "man camp" OR "workforce lodge") (beds OR units OR rooms) ("set to open" OR "under construction" OR "breaks ground" OR expansion OR opening) Texas
```
> If it floods, drop `OR expansion OR opening`, keep `"set to open" OR "under construction" OR "breaks ground"`.

---

## 2. Triage EVERY hit — route-to-market (manual for now)

This is the discipline that makes Demand Radar useful instead of a noisy news feed. For each hit, before any
outreach, assign one **bucket** + a **route tag** + an **action**, and **kill the unwinnable ones fast.**

> **Capture this MANUALLY in the existing CSV fields for now** — use `next_action` and `notes` (and
> `status` / `owner_operator`). **Do NOT add `route_to_market` / `route` as schema columns yet.** The demand
> tracker is currently empty; promoting these to first-class columns is a real schema migration (touches
> `tools/demand_radar.py` `DEMAND_HEADER`, the template + review + archive CSVs, and tests). **Only promote
> them after ~20–50 real rows show we're writing the same labels by hand repeatedly.** See §5.

**Manual capture example (in the row):**
```
status:       reviewing
owner_operator:  <fill if you can find it>
next_action:  ROUTE: account-map owner/FF&E firm; do not cold-sell property
notes:        route_to_market=channel; route=brand/FF&E; reason=branded hotel PIP likely vendor-controlled
```

### The 5 buckets (pick one)
| Bucket | Decision guidance |
|---|---|
| **direct-local** | In-region independent/owner-operated, buy-window ≤9 mo, no brand/GPO lock → log + start outreach now. |
| **channel** | Real demand but bought through an intermediary → don't chase the property; identify + log the route actor (tag below) and pursue *that*. |
| **spec-position** | Early (breaks-ground / PIP just announced, 12–24 mo out) → goal is to get specified before lock; record + set a resurface date near the buy-window. |
| **market-intel** | Useful for account/portfolio mapping but not actionable now (deprioritized segment, out-of-region, or no near-term PO) → file to intel, no outreach. |
| **reject** | Fails a kill criterion → drop. |

### Route tags (attach to direct-local / channel / spec-position)
`direct-buyer` · `owner/developer` · `ffe-procurement` (FF&E/purchasing firm runs the buy) ·
`brand-vendor` (brand-approved/standard program controls the spec — note the brand) ·
`gpo-distributor` (GPO/distributor channel — senior/healthcare/large operators; e.g. Direct Supply/DSSI,
Value First, Vizient/Premier/HealthTrust) · `public-procurement-later` (will become a public RFP → hand off
to the procurement lane ~12 mo before opening — esp. shelters/corrections/public housing) ·
`licensor-channel` (**tag only — operator-owned, not worked by the assistant**).

### Kill criteria (reject if ANY true)
- **Too late** — already "grand opening"/"now open" for a new build with no replacement angle *(exception:
  seed a replacement-cycle resurface — hotels ~7 yr; senior/student/healthcare ~8–12 yr).*
- **Too small** — below a minimum viable bed/room/unit count (e.g. <40) with no portfolio behind it.
- **Wrong segment** — not a mattress/bedding end-use, or a deprioritized segment with no operator hook.
- **Too locked** — hard national-brand standard or closed GPO with no findable entry and no PIP opening.
- **No findable route** — can't identify owner/operator/procurement contact within reasonable effort → file
  as intel, stop chasing.

---

## 3. Add the feeds to the repo
Append each verified feed to `configs/feeds.json` with the **`"kind":"demand"`** flag and the
`Demand Radar: Pilot <X> <geo>` source label (see §1). Send me the URLs and I'll wire them in.

## 4. Verify end-to-end
Dry-run one new feed:
```
python tools/ingest_rss.py --feed "<url>" --kind demand --dry-run
```
You should see `demand: N` and sample rows. Then the weekly RSS workflow populates
`leads/demand/_demand_radar.csv` and the demand section appears in your digest/email.

## 5. When to promote route-to-market into the schema (not yet)
The classifier *can* heuristically guess a bucket from cues it already extracts (segment, brand flags,
project-stage): branded hotel + early stage → spec-position; branded + opened → market-intel; institutional
(healthcare/correctional/shelter) → channel/GPO; independent hotel → direct-local. **But ownership,
franchise-vs-corporate, GPO membership, and FF&E firm cannot be inferred from an RSS headline** — those are
the parts that actually decide winnability, and only a human (or enrichment) can confirm them. So an automatic
route field would be a *hint, not truth*. **Decision: capture manually first (§2). After 20–50 real rows, if
the same labels recur, promote `route_to_market` + `route` to columns** (design ready: 2 new fields after
`project_stage` in `DEMAND_HEADER`; a `classify_route()` helper emitting hints into `reasons`/`notes`; only
`reject` ever auto-kills; migrate the 3 CSVs + 4 test files in one PR).

---

## Reference — buy-window lead times (why the radar prioritizes some signals)
Mattresses are bought near the *end* of construction, so the radar keys rows by **estimated buy-window** and
surfaces them when outreach can convert. Rough signal → mattress-PO lead time:

| Segment | Best actionable signal | ≈ lead to mattress PO |
|---|---|---|
| Hotel new-build | "set to open 20XX" / "tops out" | 4–10 mo |
| **Hotel PIP/re-flag** | **PIP / re-flag / soft-goods** | **4–12 mo (recurring, high-value — Pilot A)** |
| Senior living | "set to open" / hiring administrator | 2–7 mo (GPO/operator-routed) |
| Student housing | "delivering Fall 20XX" / now leasing | 2–6 mo (hard Aug deadline) |
| Hospital | "opens 20XX" / nearing completion | 4–13 mo (GPO-controlled — intel) |
| Correctional | tops out / staffing up | 4–10 mo — **then a public RFP** (hand to procurement lane ~12 mo before opening) |
| Shelter/workforce | announced / breaks ground | 1–9 mo (fast cycles — Pilot C) |

"Breaks ground" signals are **early** (15–24 mo out) — the radar keeps them and resurfaces near the
buy-window. "Grand opening" signals are **too late** for the new build but seed a **replacement-cycle**
follow-up (hotels ~7 yr; senior/student/healthcare ~8–12 yr).

---

## Appendix — Reserve / expansion query library (NOT in the starting pilot)

**Deprioritized to intelligence-only — add later, with a route map, only after Pilot A/B prove out:**
- **Broad branded hotel new-build** — high volume, most brand-locked; Pilot A captures the same accounts via
  the better PIP/re-flag route. Treat new-build hits as `spec-position`/`market-intel`.
- **Generic senior-living-by-metro** — add after, *with* GPO/operator mapping (Direct Supply/DSSI, Value
  First); without the channel map these aren't actionable.
- **Generic hospital / correctional by-metro** — intel-only now; correctional → `public-procurement-later`.

**Reserved campus / operator student-housing queries** (hold; activate ONE statewide alert at a time only when
bandwidth exists — operators are the route-to-market; campus-name hits are `spec-position` only):
```
("Texas A&M" OR "University of Houston" OR "UT Austin" OR "University of Texas" OR "Texas State University") ("residence hall" OR "student housing" OR dormitory OR "res hall") (renovation OR "breaks ground" OR "now leasing" OR "set to open" OR delivers) (beds OR units)
```
```
("American Campus Communities" OR "Campus Advantage" OR "Asset Living" OR "Cardinal Group" OR "Landmark Properties" OR "The Scion Group" OR "Core Spaces") ("student housing" OR "residence hall" OR beds) (Texas OR Houston OR Austin OR "College Station" OR "San Marcos")
```

**Geo expansion tokens** (clone the best-performing pilot here *after* the TX pilot proves signal quality —
add OK/LA first):
`"Oklahoma City"` · `Tulsa` · `"New Orleans"` · `"Baton Rouge"` · `Jackson Mississippi` · `"Little Rock"` ·
statewide `Oklahoma` · `Louisiana` · `Mississippi` · `Arkansas` · `"New Mexico"`.

**Original broad-segment query templates** (A–G) are retained in git history (pre-2026-06-29 version of this
file) if a future segment needs them; the reframe above supersedes the "16 broad alerts" pilot.

---

### Scope note
Operator setup runbook (docs only). The Demand Radar code is already merged; **no code/schema change is part
of this reframe** — route-to-market is captured manually until real data justifies columns (§5). Verify all
third-party feed URLs before adding. The Restonic/Spring Air licensor channel is a classification tag only,
operator-owned, never worked by the assistant. PII stays out of version control.
