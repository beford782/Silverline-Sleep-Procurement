# Demand Radar & Funnel — Next-Steps Plan

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-30
- **Status of inputs:** Demand Radar pilot is LIVE (7 feeds wired, PR #96 merged); **0 demand rows captured
  yet**; **0 active bids**; SAM.gov legal-name correction (L.P.→LLC) **submitted and in GSA review**
  (ref `INC-GSAFSD21285074`, ETA ~Jul 1–3).

This plan supersedes an external review that proposed an 8-item / 5-PR tooling build. That review's *facts*
were accurate, but its *sequencing* built cockpit/enrichment/buy-window machinery **before any real rows
exist** — which the feed-setup runbook (§5) explicitly forbids — and it ignored the highest-leverage item in
the system (SAM). The corrected plan is gated on real data and led by revenue, not tooling.

## Guiding principles
1. **SAM first.** The mature public-procurement lane converts; it is dark only because of one in-flight SAM
   correction. Re-lighting it outranks any pre-revenue radar tooling.
2. **Earn the right to build.** No Demand Radar schema/tooling changes until ~20–50 hand-triaged real rows
   show recurring patterns. Refine against real headlines, not guesses.
3. **The operator is the bottleneck**, not the tooling. Prefer work that buys back selling hours or proves
   conversion; avoid adding maintenance surface to a single-operator system.
4. **Route-to-market, honestly.** For institutional mattresses the property is rarely the buyer (brand
   standard / FF&E firm / GPO). Pilot **B** (independent hospitality) is the real direct-lead lane; **A**
   (hotel PIP/re-flag) is mostly market-intel / spec-positioning; **C** (shelter/workforce) is fast-cycle but
   sparse and often routes back to public RFP. Realistic conversion order: **B > C > A.**
5. **Weak source ⇒ better sources, not better parsing.** Google Alerts is a cheap signal *test*. If it's thin
   on real PIPs/FF&E awards (likely), the fix is the **permit open-data adapter** / hospitality trade feeds —
   not headline NLP.

---

## Phase 0 — Revenue switches (now)
| # | Action | Owner | Exit criteria |
|---|--------|-------|---------------|
| 0.1 | **Land SAM** — watch for the GSA email on `INC-GSAFSD21285074` → complete validation → re-enter registration (`scratchpad/sam_registration_reentry_data.md`) → IRS taxpayer step. Hard rules until active: no banking, don't cite UEI `XF73FG8CVMX1`. | Operator (+ assistant watches inbox) | SAM entity **Active**; VA/BOP/Army channels re-lit. |
| 0.2 | **PR1 — doc/checklist truth-up** (this PR). | Assistant | Merged, CI green. |

## Phase 1 — Earn the data (next 4–6 weeks)
No new tooling. Generate the rows that license Phase 2/3.
- **1.1** Run the 7 pilot feeds as-is (Mon/Thu ingest, already wired).
- **1.2** Hand-triage **every** hit per `demand_radar_feed_setup.md` §2 (bucket + route tag + next action +
  kill criteria). Route/owner captured **manually** in `next_action` / `notes` / `owner_operator`. No schema
  change.
- **1.3** **Conversion tally** (the missing metric): tag each row's end-state in `notes` —
  `route-mapped` / `conversation` / `quote` / `dead`. This is what proves the lane is worth operator time.
- **1.4** Re-aim: treat **B** as the direct-lead lane, **A** as intel/spec-positioning, and add **one
  statewide Pilot C feed** to test the fast-cycle lane.

**Exit gate:** ~20–30 triaged rows with outcome tags. Phases 2–3 stay closed until then.

## Phase 2 — Thin tooling (gated on Phase 1 rows; typed-columns only)
- **2.1** `demand_radar.py summary` additions over **existing typed columns**: "needs-triage" count,
  90/180-day buy-window split, "empty `owner_operator`" backlog.
- **2.2** *Optional, pure logic:* `estimate_action_window()` + brand/city helpers as **pure, unit-tested
  functions** in `demand_signal.py` — **not** wired into the persisted schema or sort order yet.
- **Dropped from the external plan:** the cockpit's "missing route tag" check (it greps free-text `notes`,
  which has multiple writers — brittle) and headline/brand/city *extraction into the schema* (validatable
  only against real headlines).

## Phase 3 — One atomic migration (gated on ~20–50 rows + recurring hand-labels)
`leads/demand/_demand_radar.csv` uses the **exact-match reader** (`read_demand_rows` raises on any header
drift — same discipline as `lead_radar`), so a column add is a coordinated multi-file migration, not a cheap
append. Do it **once**, folding the external plan's PR3+PR4+PR5 together:
- Bump `DEMAND_HEADER` a single time: add **`est_action_window`** (keep `est_buy_window`, fall back
  old→new — do **not** mutate the meaning of the existing field; 4 consumers read it) + only the
  route/triage columns whose labels actually recurred (`route_to_market` / `route_tag` / `triage_bucket` /
  `follow_up_date`).
- Migrate both CSVs + `templates/demand_radar_tracker.csv` + every pinned test **in the same PR** (or the
  next ingest hard-fails on the non-zero-exit path).
- Switch summary/digest sort to `est_action_window` (fallback `est_buy_window`).
- Finalize `demand_match_keys` dedup enrichment **in this same window** — changing the dedup key after rows
  accumulate risks re-ingesting "new" dupes or swallowing distinct rows.
- Calibrate the action-window offsets against the **real rows** now in hand.

## Parallel / conditional
- **Source escalation:** if Phase 1 signal is thin, build the **municipal permit open-data adapter** (already
  on `system_overview.md §7`) ahead of any Demand-Radar UI work.
- **Out of scope:** the Restonic / Spring Air **licensor channel** stays a classification tag only —
  operator-owned, never worked by the assistant.

---

*Why this order: the external review's own "wait for 20–50 rows before adding automation" rec was the right
instinct; this plan follows it consistently instead of building the cockpit the rows haven't earned. See
`docs/research/strategic_review_2026-06-28.md` for the upstream strategy and `demand_radar_feed_setup.md` for
triage mechanics.*
