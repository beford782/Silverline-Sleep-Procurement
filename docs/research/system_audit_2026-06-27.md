# Silverline Procurement System — Full Audit (2026-06-27)

- **For:** Blake / Continental Silverline Products, LLC
- **Method:** Multi-agent audit — 7 dimension finders (coverage, relevance engine, ingest pipeline, data integrity, pipeline discipline, runbooks/backlog, tests/CI) → adversarial verification of every finding against the real code/data (default-to-refuted) → synthesis. 15 agents, ~880K tokens.
- **Result:** 48 verified defects, 44 improvement opportunities.
- **Scope:** Read-only audit. This document is the record; fixes ship as separate PRs.

> **PII note:** one critical finding is a street-address leak in `leads/review/_lead_radar.csv`. The address is **redacted** in this report (shown as `[street address — redacted]`) so the report itself does not re-commit the PII. Fix the underlying CSV row separately.

> **⚠️ CORRECTION (2026-06-27):** This audit's "LLC-vs-L.P." guidance had the entity **backwards**. The
> real entity is **CONTINENTAL SILVERLINE PRODUCTS, LLC** (a Texas LLC); there is no L.P. Any finding/
> recommendation below that says to standardize on "L.P." is **superseded** by
> [`entity_correction_plan_2026-06-27.md`](entity_correction_plan_2026-06-27.md). The canonical
> `company_identity.md` and the SAM runbook have been corrected to LLC.

---

## Executive summary

The system is structurally sound and the core discipline (empty active pipeline, human triage, no-bid memos) is being held — but it holds by *convention, not code*, and its dominant failure mode is **silent misses**, the exact class that already cost the ~90-fit Bernalillo correctional RFB. Three systemic weaknesses recur: (1) scheduled ingest jobs swallow RSS/SAM fetch failures and report green, with zero failure alerting; (2) the relevance engine both under-recalls (SAM sweep is a single `title="mattress"` substring) and mis-signals premium fits (anti-ligature penalized, `aviation`/disposal hard-rejects fire before STRONG `mattress`); and (3) governance state (registry status, gate columns, ledger-vs-Radar) is unenforced, so drift is undetectable. One **critical** item gates all federal revenue: SAM.gov is not Active (EFT banking is the last operator step), and a hard NM Euna/Bonfire cutover lands **2026-06-29 (2 days out)**. The three highest-leverage actions: **(a)** add an `if: failure()` alert + reject-log to every scheduled workflow so misses become visible; **(b)** complete the NM registration before 06-29 and finish SAM banking, fixing the runbook's LLC-vs-L.P. trap first; **(c)** broaden SAM recall (NAICS 337910 + title sweeps) and fix the relevance precedence/anti-ligature inversions.

> **Status update (2026-06-27):** The **NM Euna/Bonfire registration is now COMPLETE** (done after this audit's data snapshot) — all 4 steps green, clean 15-code commodity set, Opportunity Recommendations on. The NM line items below were captured before that and are largely closed; the SAM-banking critical remains open.

## Defect list (prioritized)

| Issue | Dimension | Location | Fix |
|---|---|---|---|
| **SAM.gov not Active — EFT banking is the open resume point blocking ALL federal awards** | runbooks-backlog | `docs/active_registrations.md:19,82`; `docs/sam_uei_unblock_runbook.md:17` | Complete Financial/EFT section per runbook §6, submit, await TIN match + CAGE; flip ledger to active. |
| Scheduled SAM workflow re-scores with discredited substring scorer, clobbering relevance fit_score (re-fires `cot`/`foundation` bug) | relevance-engine / pipeline-discipline | `tools/pipeline.py:395-417,456`; `weekly_sam_ingest.yml:75`; `ingest_sam.py:278` | Drop re-score for relevance-ingested rows, or make `score_text` word-boundary and seed from `verdict.confidence`. |
| HARD_EXCLUDE evaluated before include signals — `mattress + recycling/disposal/reupholster` buys silently REJECTed, no review trail | relevance-engine | `relevance.py:198-201,77-84`; `ingest_sam.py:279-282` | When STRONG_INCLUDE present, demote disposal/recycling/reupholster to REVIEW; reserve hard-reject for unambiguous families. |
| HARD term `aviation` collides with real `DLA Aviation` buyer name (folded into matched blob, runs first) | relevance-engine | `relevance.py:80,196,198-201`; `ingest_sam.py:276` | Match `aircraft`/`aviation` against product text only, not buyer/source; or only hard-reject when no STRONG term present. |
| Anti-ligature / ligature-resistant treated as penalty + forced high-risk — inverts the premium correctional fit signal | relevance-engine | `relevance.py:90-91,216-218`; `pipeline.py:101,125,400,405-406` | Remove from SOFT_EXCLUDE and CAUTION/STRONG_CAUTION; treat as positive correctional/behavioral-health term. |
| Scheduled SAM recall = single title substring `mattress`; no NAICS/PSC/bedding sweep (Bernalillo-class recall gap) | relevance-engine | `weekly_sam_ingest.yml:53-57`; `ingest_sam.py:305-309` | Add scheduled queries on NAICS 337910, PSC 7210/7105, and title sweeps (`box spring`,`bedding`,`bunk`); dedupe. |
| Lead-archive excluded from dedup — human-triaged dead leads re-ingested every sweep | ingest-pipeline | `ingest_email.py:865,449-455`; `ingest_rss.py:314,216-220`; `lead_radar.py:416-461` | Load `lead_radar.DEFAULT_ARCHIVE` and fold its match keys into the lead dedup set (mirror the bid path). |
| RSS feed fetch failures (Bonfire 403) swallowed; run reports green | ingest-pipeline | `ingest_rss.py:326-336,370`; `weekly_rss_ingest.yml:33-60` | Track fetched-vs-failed counts; emit `::warning::` / non-zero on any feed error. |
| SAM 429 throttle yields empty result, exit 0, no retry/backoff (throttle indistinguishable from empty week) | ingest-pipeline / tests-ci | `ingest_sam.py:334-340,399-404`; `weekly_sam_ingest.yml:57` | Bounded retry honoring `Retry-After`; emit a distinct throttled signal in the digest. |
| Scheduled ingest jobs have zero failure alerting — a crashed run is silent | tests-ci | `weekly_sam_ingest.yml`, `weekly_rss_ingest.yml`, `procurement_digest.yml` | Add `if: failure()` step that opens/comments a GitHub issue (reuse digest's gh-issue pattern). |
| Hard rule (active = confirmed fit only) enforced by convention, not code; ingest auto-writes ACCEPT/REVIEW to active | pipeline-discipline | `ingest_sam.py:283-293,455`; `ingest_email.py:441,501-509`; `pipeline.py:256-366` | Route non-confirmed signals to Lead Radar/triage gate; require explicit `promote --confirmed-products`. |
| `gate_status`/`procurement_risk`/`compliance_blocker` are inert — set at ingest, never enforced or recomputed | pipeline-discipline | `ingest_sam.py:240-242`; `pipeline.py:419-461`; `workflow_check.py:139-197` | workflow_check ERROR when status in {drafting,submitted,awarded} while gate=blocked or blocker non-empty; clear blocker on state transitions. |
| NM-SPD Euna/Bonfire was partial — eProNM window closed 06-22, exclusive go-live 2026-06-29 (**now resolved — registration complete 2026-06-27**) | runbooks-backlog / coverage | `active_registrations.md:50`; `nm_spd_euna_bonfire_registration_runbook.md:35-46` | DONE — Euna/Bonfire registration complete; ledger flipped. |
| SAM runbook embeds the recurring LLC-vs-L.P. error it exists to prevent | runbooks-backlog | `sam_uei_unblock_runbook.md:41,49,60` | Change to "TX limited liability company (L.P.)", "Certificate of Formation", add `L.P.` to suffix example. |
| Out-of-state university residence-life coverage absent (AR/NM) + omits top TX systems (Texas State Univ #4, ~11,300 beds) | coverage-gaps | `procurement_sources.json` (university rows); `opportunity_expansion_plan_2026-06.md:111,121,163` | Add rows for Texas State Univ System, Texas Tech, Sam Houston, UNT, NMSU, UNM, U of Arkansas (MS covered by IHL feed). |
| ingest_sam has no Lead Radar routing — REVIEW items pollute active pipeline (inconsistent with email channel) | pipeline-discipline | `ingest_sam.py:283-292,455`; `ingest_email.py:428-432,487-500` | Port `review_target='leads'` routing into ingest_sam with same dedup logic. |
| Relevance REJECTs discarded with no audit trail (no workflow passes `--reject-log`; ingest_sam has no such option) | ingest-pipeline | `ingest_sam.py:279-282`; `weekly_*_ingest.yml` | Add `--reject-log` to ingest_sam; pass a committed reject-log path in all three workflows. |
| Confirmed co-ops (Region 4 ESC/OMNIA, EPIC6/Region 6 ESC) missing from machine-readable registry; plan/ledger contradiction | coverage-gaps | `procurement_sources.json` vs `active_registrations.md:34-35`; `source_review.py:45-59` | Add Region 4 ESC row; reconcile EPIC6 skip-vs-confirmed contradiction. |
| TDCJ has an RSS feed but no source-registry row (absent from operator review checklist) | coverage-gaps | `feeds.json:14-17` vs `procurement_sources.json` | Add a TDCJ state_portal registry row (intake rss, geography TX). |
| Source registry has no status/monitoring-health field — "registered but not receiving alerts" not detectable | coverage-gaps | `procurement_sources.json` (schema); `active_registrations.md:57` | Add `monitoring_status`/`last_verified`; have source_review surface/filter on it. |
| Company street address committed to Lead Radar CSV — violates own PII rule | data-integrity | `leads/review/_lead_radar.csv:21`; rule `active_registrations.md:9,88` | Replace with `[address on file]`; add CI grep guard. **[street address — redacted in this report]** |
| posted_date conflates true publish date with sweep date, producing `due_date < posted_date` inversions on 4 rows | data-integrity | `_lead_radar.csv:2,3,9,29` | Define posted_date = publication date; keep sweep date in created_date; add soft warn on posted>due. |
| Completed Arkansas IonWave / AR Bid registration absent from ledger (Radar/ledger desync) | data-integrity | `_lead_radar.csv:37` vs `active_registrations.md:49,56-63` | Add AR IonWave row, status activated (2026-06-24). |
| High-conviction buyer clusters lack dedicated rows (TJJD, HHSC state hospitals, housing authorities) | coverage-gaps | `procurement_sources.json`; `opportunity_expansion_plan_2026-06.md:103,148` | Add named rows or document ESBD/PHA-feed coverage to close the apparent gap. |
| Full state-name detection demotes in-region ACCEPTs on county/city name collisions (`Washington County` -> WA) | relevance-engine | `relevance.py:149-152,171-175,229-233` | Prefer `, ST` USPS-code form; treat lone ambiguous place name as unknown-geography. |
| `bedding`/`linens` WEAK-only — `Inmate Bedding` never auto-enters active pipeline | relevance-engine | `relevance.py:58-65,219-222` | Promote `inmate/jail/correctional bedding` to STRONG; keep bare `bedding`/`linens` weak. |
| Auto-ingest PRs never run full CI (machine-path leak check, JSON parse, whitespace omitted) | tests-ci | `weekly_sam_ingest.yml:77-95,145-151`; `ci.yml:35-39,83-91,93-98` | Factor CI checks into a reusable composite workflow invoked from both, or push a follow-up commit from a non-GITHUB_TOKEN identity. |
| No regression test pins home-state (esp. NM) coverage in `HOME_STATES_DEFAULT` | tests-ci | `tests/test_relevance.py:33-37,118-126`; `relevance.py:39` | Parametrized test asserting each default home state keeps an in-region mattress RFB ACCEPT + NM characterization test. |
| Ledger open-tasks ordering buries the only hard-deadline task (NM 06-29) below deadline-free co-op tasks | runbooks-backlog | `active_registrations.md:82-85` | Reorder NM right after SAM; annotate with deadline. |
| SAM runbook treats already-no-bid JBSA FA301626Q0151 as a pending mattress fit | runbooks-backlog | `sam_uei_unblock_runbook.md:86,149-152` | Note JBSA no-bid 2026-06-25 (product mismatch); redirect to genuine VA/BOP/DoD-bedding channels. |
| Ledger/Radar desync on BuyBoard registration state | data-integrity | `active_registrations.md:39,84` vs `_lead_radar.csv:4` | Set ledger to in-progress; clarify remaining task is the membership application. |
| `--allow-throttled-empty` always passed — throttle approx genuine empty week at job-status level | tests-ci | `weekly_sam_ingest.yml:57`; `ingest_sam.py:399-404` | Bounded retry + distinct labeled digest signal. |
| Healthcare/LTC GPO channel (Vizient/Premier/HealthTrust) unmonitored | coverage-gaps | `procurement_sources.json`; plan:193 | Defer — conditional on adding a healthcare support-surface line. |
| PATTERN Bonfire feeds + Google-Alert RSS not yet added | coverage-gaps | `configs/feeds.json`; plan:311,332,347 | Dry-run-verify 6 PATTERN subdomains; stand up Google Alerts as RSS. Backlog, by design. |
| PROCUREMENT_CUES includes bare `bid`/`quote`/`proposal` — weakens RSS require_procurement gate | relevance-engine | `relevance.py:97-104,235-238` | Require multi-word phrases (`bid number`, `request for proposal`). |
| Gmail-path posted_date always overwritten with today (RFC-822 Date never parsed) | ingest-pipeline | `ingest_email.py:370,616` | Use `email.utils.parsedate_to_datetime` (as ingest_rss already does). Non-default path. |
| No per-message exception isolation in email batch loop (one bad email aborts the sweep) | ingest-pipeline | `ingest_email.py:468-510,867-870` | Wrap per-unit body in try/except -> `skipped` bucket. Fails loud, not silent. |
| RSS feeds force-decoded UTF-8 (`errors='replace'`) — mojibake on Windows-1252 feeds | ingest-pipeline | `ingest_rss.py:272-276` | Honor HTTP/declared charset or pass raw bytes to `ET.fromstring`. |
| Month-abbrev due dates with trailing period dropped (`Jun. 5, 2026`) | ingest-pipeline | `ingest_email.py:154-172,200-208` | Strip trailing `.` from month token before strptime. |
| IonWave digest sub-blocks with no parseable title silently discarded | ingest-pipeline | `ingest_email.py:338-352` | Count/surface discarded blocks; emit generic single-row fallback. |
| Future-dated `last_reviewed=2026-06-29` on 6 Lead Radar rows | data-integrity | `_lead_radar.csv` L18,26,27,30,32,33 | Correct to 2026-06-22; add future-date assertion to `lead_radar.py` validation. |
| No schema enforcement separating blank from missing (empty posted_date, many empty fit_score) | data-integrity | `_lead_radar.csv:19` | Backfill omnia row; add workflow_check WARN for due_date+fit_score but no posted_date. |
| SAM-not-Active timing no-bids archived terminally (no `blocked`/`parked` status) | pipeline-discipline | `bids/archive/...uscg-base-boston...`; `pipeline.py:69` | Add parked/blocked lifecycle + recurring Lead Radar channel watch. |
| SAM runbook Financial section mis-numbered (`## 6` header, `7a–7e` subsections collide with `## 7. Sources`) | runbooks-backlog | `sam_uei_unblock_runbook.md:90,98-156` | Renumber subsections 6a-6e. |
| Digest recent-runs filter uses a workflow name that never matches the email workflow | tests-ci | `procurement_digest.yml:77` vs `weekly_email_ingest.yml:1` | Match real name or filter by workflow file path. |
| Scheduled workflows lack `timeout-minutes` and `concurrency` controls | tests-ci | `.github/workflows/*` | Add `timeout-minutes` + `concurrency` group per job. |

## Improvement roadmap (ROI-ranked)

| Improvement | Impact | Effort | Dimension | First concrete step |
|---|---|---|---|---|
| **DO-NOW: `if: failure()` alert step on every scheduled ingest workflow** | high | low | tests-ci | Copy `procurement_digest.yml:97-111` gh-issue pattern into a final `if: failure()` step on SAM/RSS/email workflows. |
| **DO-NOW: Broaden the scheduled SAM sweep beyond `title="mattress"`** | high | low | relevance-engine | Add `--naics-code 337910` pass + title sweeps (`bedding`,`bunk`,`box spring`,`cot`) to `weekly_sam_ingest.yml:54`; dedupe across queries. |
| **DO-NOW: One canonical `docs/company_identity.md` + fix SAM runbook LLC->L.P.** | high | low | runbooks-backlog | Create identity card (legal name, TX Limited Liability Company, Certificate of Formation, UEI XF73FG8CVMX1, NAICS 337910/337127, PSC 7210/7105); edit `sam_uei_unblock_runbook.md:41,49,60`; link from all runbooks. |
| Reorder `classify()` so STRONG_INCLUDE overrides ambiguous HARD_EXCLUDE families | high | low | relevance-engine | Split HARD_EXCLUDE into unambiguous kills vs context terms (disposal/recycling/reupholster/`aviation`); route STRONG+context to REVIEW. |
| Promote anti-ligature/ligature-resistant from penalty to STRONG fit signal | high | low | relevance-engine | Remove from `relevance.py:90-91` SOFT_EXCLUDE and `pipeline.py:101,125` CAUTION/STRONG_CAUTION; add to correctional vocab. |
| Consult the lead archive for dedup | high | low | ingest-pipeline | Feed `lead_radar.DEFAULT_ARCHIVE` keys into `lead_ids` in `ingest_email.py:451-455` and `ingest_rss.py:216-220`. |
| Always write a committed reject log in scheduled runs | high | low | ingest-pipeline | Add `--reject-log` to ingest_sam; pass `logs/rejects/_<source>.csv` in all three workflows (`_append_reject_log` already exists). |
| Give ingest_sam the same `review_target='leads'` default as ingest_email | high | low | pipeline-discipline | Build Lead Radar row on REVIEW via `lead_radar.build_lead_row` instead of appending to active. |
| Add gate-consistency checks to `workflow_check.py` | high | low | pipeline-discipline | ERROR when status in {drafting,submitted} while gate=blocked or blocker non-empty; makes the 3 governance columns load-bearing. |
| CI CSV validator (future dates, posted>due, column count, required fields) | high | low | data-integrity | Extend `workflow_check.py:161` staleness logic; wire into `ci.yml` — would have caught the 6 future dates + 4 inversions. |
| Pre-commit/CI PII linter (street address, EIN, phone, CMBL) | high | low | data-integrity | Regex scan tracked text files; allowlist public UEI; block on match. |
| Relevance regression tests pinning each home state + Bernalillo characterization | high | low | tests-ci | Parametrized assert `jail mattress, Albuquerque NM` -> ACCEPT for NM/TX/LA/MS/AR/OK in `test_relevance.py`. |
| Add TDCJ registry row + verify Bonfire feed is producing | high | low | coverage-gaps | Add TDCJ state_portal row; confirm `tdcj.bonfirehub.com` RSS returns items; add ESBD saved search as 2nd channel. |
| Add Region 4 ESC/OMNIA + Equalis co-op rows with real intake | high | low | coverage-gaps | Add registry rows; set intake to verified email/saved-search alerts, not generic `manual_review`. |
| RSS quick-wins: 6 PATTERN Bonfire + Google-Alert RSS | medium | low | coverage-gaps | Dry-run-verify PATTERN subdomains; add ones returning valid XML; stand up Google Alerts as RSS deliveries. |
| Add TJJD + housing-authority registry rows | medium | low | coverage-gaps | Add TJJD row + registry entries backing the 2 existing PHA feeds. |
| Make relevance.py the single source of fit_score; retire `score_text` | high | medium | relevance-engine | Have `cmd_score` delegate to `relevance.classify`; stop overwriting relevance-derived fit_score. |
| Retry-with-backoff + surface fetch failures as non-zero/notification | high | medium | ingest-pipeline | Wrap `fetch_feed`/`fetch_page` in 3-try exponential backoff; track per-source failure count -> non-zero exit. |
| Make the hard rule a code gate (triage holding state + explicit promotion) | high | medium | pipeline-discipline | Route ingest ACCEPTs through `lead_radar.promote` (`--confirmed-products`, `lead_radar.py:582-587`) or gate on `gate_status='bid_ready'`. |
| Add status/monitoring-health field to registry + ledger reconciliation | high | medium | coverage-gaps | Add `monitoring_status`/`last_verified`; add a source_review reconciliation diff against the ledger. |
| Stand up TX HHSC State Hospitals/SSLCs channel | high | medium | coverage-gaps | Create ESBD saved searches (SA 300-bed, Rusk, Kerrville 2027) + buyer registry row. |
| Add residence-life rows for AR/MS/NM + top TX university systems | high | medium | coverage-gaps | Add Texas State Univ System first, then NMSU/UNM/U of Arkansas (MS covered by IHL feed). |
| Regression corpus of real titles/buyers (Bernalillo, DLA Aviation, disposal-bundled, ligature) | high | medium | relevance-engine | Encode each past miss as a test asserting expected decision band. |
| Ledger/Radar reconciliation script | high | medium | data-integrity | Parse registration status/account IDs from Radar notes; diff against ledger tables every sweep. |
| Throttled-empty distinguishable from genuine-empty (sentinel + retry) | high | medium | tests-ci | On 429, set step output `throttled=true` + single retry; digest reports "SAM THROTTLED — re-run needed". |
| Run full ci.yml check set in pre-PR step of ingest workflows | medium | low | tests-ci | Copy leak/JSON/whitespace checks (`ci.yml:83-98`) into each pre-PR step. |
| Constrain geography demotion to comma/state-code context | medium | low | relevance-engine | Only demote out-of-region on `, ST` or `State of X` forms, not bare place names. |
| Deadline-aware "next up" view on the ledger | medium | low | runbooks-backlog | Add deadline column to open-tasks; order by it; banner for tasks within ~7 days. |
| Provider-agnostic email date parsing + month-period strip | medium | low | ingest-pipeline | Reuse `ingest_rss.py:119-124` RFC-822 handling in `normalize_date`. |
| Fix + de-fragilize digest recent-runs filter | medium | low | tests-ci | Filter `gh run list` by workflow file path instead of display name. |
| Post-Active SAM renewal checklist + expiration reminder | medium | low | runbooks-backlog | On Active, capture CAGE + expiration in ledger row; reminder ~60 days prior. |
| Split posted_date into discovery_date + published_date | medium | medium | data-integrity | Add `published_date` column; backfill 4 inverted rows. |
| Open Vizient non-acute "Beds, Mattresses & Overlays" GPO lane | medium | medium | coverage-gaps | Deferred — gate on adding a healthcare support-surface product line. |
| Tighten PROCUREMENT_CUES to multi-word phrases | low | low | relevance-engine | Drop bare `bid`/`quote`/`proposal` from `relevance.py:103-104`. |
| Add `timeout-minutes` + `concurrency` to scheduled workflows | low | low | tests-ci | Two lines per workflow. |
| Honor declared charset when decoding feeds | low | medium | ingest-pipeline | Pass raw bytes to `ET.fromstring` (respects XML declaration). |

## What's working well — don't break these

- **The empty active pipeline + human-promote discipline is being honored**, and the no-bid memos (USCG Base Boston, JBSA) are thorough and correctly catch product mismatch — keep the convention while making it executable, don't weaken the gate.
- **`relevance.py` already fixed the substring-matching bug** (whole-word boundaries so `cot` != `Scott`, `foundation` doesn't false-fire) — preserve this; the remaining work is stopping `pipeline.score_text` from overwriting it, not re-litigating the matcher.
- **RSS per-feed isolation and the `--allow-throttled-empty` design intent are reasonable foundations** — the fixes are additive (surface failures, retry), not rewrites; the 11 VERIFIED Bonfire feeds were correctly added and the MS IHL/PHA feeds already provide real coverage.
- **The ledger is genuinely actively managed** (recent commit corrected the NM cutover date; each registration carries explicit status/notes) — the gap is machine-readability and sync enforcement, not operator diligence.
