# Demand Radar — Feed Setup Runbook (turn the private funnel ON)

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-28
- **What:** The Demand Radar engine is built and merged (`tools/demand_signal.py`, `tools/demand_radar.py`,
  `kind:"demand"` routing in `ingest_rss.py`, digest/email surfacing). It has **no demand feeds yet**.
  This runbook is the one-time operator setup to feed it — mostly **creating Google Alerts as RSS**, which
  only you can do (Google's Alert RSS URLs are generated in the Alerts UI; they can't be hand-built).
- **How it flows once set up:** each feed → `ingest_rss.py` (demand lane) → `demand_signal.classify_demand`
  → `leads/demand/_demand_radar.csv` (keyed by estimated buy-window) → your digest/email "Demand Radar"
  section → you/sales do outreach (`python tools/demand_radar.py outreach <id> --contact ...`).

> **PII / caution:** the trade-press RSS URLs below are from general knowledge and **must be verified**
> (open the site, confirm it returns RSS/Atom XML) before adding to `configs/feeds.json`. The Google
> Alerts feeds are created by you and are self-verifying.

---

## Step 1 — Create the Google Alerts (deliver as RSS)

For each query: go to **google.com/alerts**, paste the query, click **Show options** →
**Deliver to = RSS feed**, **Sources = Automatic**, **How many = All results**, create it, then copy the
RSS feed URL (the orange RSS icon on the manage-alerts page). Google honors quoted phrases and `OR` (caps).

**Pilot first (16 feeds): the 4 highest-value segments × the 4 TX metros**, then expand. Clone each query
across these location tokens by replacing `<LOC>`:
`Houston` · `Dallas OR "Fort Worth"` · `Austin` · `"San Antonio"` · (then) `"Oklahoma City"` · `Tulsa` ·
`"New Orleans"` · `"Baton Rouge"` · `Jackson Mississippi` · `"Little Rock"` · and statewide `Texas`,
`Oklahoma`, `Louisiana`, `Mississippi`, `Arkansas`, `"New Mexico"`.

**A. Hotels — new build**
```
("breaks ground" OR "under construction" OR "topped out" OR "set to open" OR "slated to open") (hotel OR suites OR resort) (keys OR rooms) <LOC>
```
**B. Hotels — PIP / renovation / re-flag** (direct mattress-replacement signal)
```
("property improvement plan" OR PIP OR renovation OR "re-flag" OR rebrand OR "soft goods") (hotel OR Marriott OR Hilton OR Hyatt OR Wyndham OR "Holiday Inn") <LOC>
```
**C. Senior living / assisted living / memory care**
```
("breaks ground" OR "under construction" OR "set to open" OR expansion) ("assisted living" OR "memory care" OR "senior living" OR "skilled nursing") (beds OR units) <LOC>
```
**D. Student housing** (also clone by campus name: `"University of Houston"`, `"Texas A&M"`, `"University of Oklahoma"`, `LSU`, `"University of Arkansas"`)
```
("breaks ground" OR "under construction" OR "now leasing" OR delivers OR "set to open") ("student housing" OR "residence hall" OR dormitory OR "purpose-built student") (beds OR units) <LOC>
```
**E. Hospitals / patient beds**
```
("breaks ground" OR "under construction" OR "bed tower" OR "patient tower" OR "new hospital" OR expansion) (hospital OR "medical center" OR "behavioral health" OR "psychiatric hospital") (beds OR "patient beds") <LOC>
```
**F. Correctional / detention** (also clone by county)
```
("breaks ground" OR "under construction" OR "new jail" OR "detention center" OR "jail expansion") (beds OR inmate) <LOC>
```
**G. Shelter / behavioral-health crisis / workforce housing**
```
("breaks ground" OR "under construction" OR "set to open") ("homeless shelter" OR "navigation center" OR "transitional housing" OR "workforce housing" OR "crew housing") (beds OR units) <LOC>
```

## Step 2 — Trade-press RSS feeds (verify each before adding)

These carry the same signals at higher quality than Google Alerts. **Confirm each still publishes RSS**
(many trade sites dropped RSS for email newsletters — where RSS is gone, use a Google Alert
`site:domain.com (breaks ground OR opens OR renovation)` instead).

| Segment | Publication (verify the feed URL) |
|---|---|
| Hospitality | Hotel Business · Hotel Management · HotelNewsResource · Lodging (AAHOA) · HOTELS Magazine |
| Senior living | Senior Housing News · McKnight's Senior Living · McKnight's Long-Term Care · Senior Living Foresight |
| Student housing | Student Housing Business · University Business · Multi-Housing News (student vertical) |
| Healthcare construction | Healthcare Design · Health Facilities Management · Becker's Hospital Review |
| Correctional | Correctional News · Corrections1 |
| Regional / general | ENR Texas & Louisiana / ENR Southwest · Construction Dive · the city Business Journals (Houston/Dallas/Austin/SA/NOLA/OKC/Little Rock) · REBusinessOnline |

## Step 3 — Add the feeds to the repo

Append each verified feed to `configs/feeds.json` with the **`"kind":"demand"`** flag (this is what sends
it through the demand classifier instead of the procurement one):
```json
{ "source": "Demand Radar: hotels new-build Houston", "url": "<the Google Alerts RSS URL>", "kind": "demand" }
```
Send me the URLs and I'll add them (and keep the `source` labels consistent so the digest groups them).
Existing procurement feeds need no change (absent `kind` defaults to `procurement`).

## Step 4 — Verify end-to-end

Run a dry run against one new feed:
```
python tools/ingest_rss.py --feed "<url>" --kind demand --dry-run
```
You should see `demand: N` and sample rows. Then the weekly RSS workflow will populate
`leads/demand/_demand_radar.csv` and the demand section appears in your digest/email.

---

## Reference — buy-window lead times (why the radar prioritizes some signals)

Mattresses are bought near the *end* of construction, so the radar keys rows by **estimated buy-window**
and surfaces them when outreach can convert. Rough signal → mattress-PO lead time:

| Segment | Best actionable signal | ≈ lead to mattress PO |
|---|---|---|
| Hotel new-build | "set to open 20XX" / "tops out" | 4–10 mo (**act**) |
| Hotel PIP/re-flag | PIP / re-flag / soft-goods | 4–12 mo (**recurring, high-value**) |
| Senior living | "set to open" / hiring administrator | 2–7 mo |
| Student housing | "delivering Fall 20XX" / now leasing | 2–6 mo (hard Aug deadline) |
| Hospital | "opens 20XX" / nearing completion | 4–13 mo |
| Correctional | tops out / staffing up | 4–10 mo — **then it becomes a public RFP** (hand off to the existing procurement lane ~12 mo before opening) |
| Shelter/workforce | announced / breaks ground | 1–9 mo (fast cycles) |

"Breaks ground" signals are **early** (15–24 mo out) — the radar keeps them and resurfaces them near the
buy-window rather than discarding. "Grand opening" signals are **too late** for the new build but seed a
**replacement-cycle** follow-up (hotels ~7 yr; senior/student/healthcare ~8–12 yr).

### Scope note
Operator setup runbook (docs only). The Demand Radar code is already merged. Verify all third-party feed
URLs before adding. PII stays out of version control.
