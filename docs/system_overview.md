# System Overview — Silverline Procurement & Demand Funnel

- **For:** Blake / Continental Silverline Products, LLC
- **Last updated:** 2026-06-28
- **What this is:** the living architecture doc — how the whole system works end to end, what each
  component does, and where the human sits in the loop. Start here to understand the system; the deep
  strategy/rationale is in [`research/strategic_review_2026-06-28.md`](research/strategic_review_2026-06-28.md).

## 1. Mission (one line)
Be a **funnel** that surfaces the **best** and **all** institutional-mattress opportunities — **public**
(government bids) and **private** (pre-RFP construction demand) — ranked by what we can actually **win**,
and never silently miss one.

It runs as **two parallel lanes** feeding one ranked, human-gated output:

```
                     ┌─ PROCUREMENT lane (public bids: "who's buying now") ─┐
 SOURCES ─ INGEST ──┤                                                       ├─ RANK ─ SURFACE ─ ACT
                     └─ DEMAND lane (private pre-RFP: "who'll buy soon") ────┘
```

## 2. End-to-end flow
**Sources → Ingest → Classify → Route → Rank → Surface → Act** — automated on a schedule (GitHub
Actions), with humans gating the two decisions that matter: what enters the active bid pipeline, and who
gets outreach.

### Stage 1 — Sources
Three mechanical intake shapes (everything must arrive as one of these):
- **RSS/Atom** — `configs/feeds.json` (government Bonfire tenants; **demand feeds** added here with `kind:"demand"`).
- **JSON API** — SAM.gov contract opportunities.
- **Email (IMAP)** — portal alert emails (IonWave/BidNet/BuyBoard/ESBD/co-ops) forwarded to the
  `silverlinesleep.com` inbox, since those portals have no public feed/API.

Registry of what we're registered to: [`active_registrations.md`](active_registrations.md) and
`sources/procurement_sources.json`.

### Stage 2 — Ingest (the adapters)
| Tool | Source |
|---|---|
| `tools/ingest_rss.py` | RSS/Atom feeds; routes each by `kind` (procurement vs demand) |
| `tools/ingest_sam.py` | SAM.gov (title + NAICS 337910 + PSC 7210/7105 sweeps, deduped) |
| `tools/ingest_email.py` | IMAP mailbox; unwraps forwarded portal alerts |
| `tools/ingest_portal_csv.py` (+ `portal_csv_mapping.py`) | manual portal-export paste fallback |

All adapters dedupe against prior rows **including archives**, so dead leads don't re-enter each sweep.

### Stage 3 — Classify (two brains)
- **`tools/relevance.py`** (`classify`) — the **procurement** brain. Decides if text is a real
  mattress/bedding *solicitation*: STRONG/WEAK include terms, procurement cues (RFP/IFB/solicitation),
  exclude tiers (air/concrete mattress → hard reject; aviation/disposal → demote). Returns
  **ACCEPT / REVIEW / REJECT** + confidence 0–100 + detected states. **This is the single source of
  product-fit; do not retune it casually — everything downstream consumes its confidence.**
- **`tools/demand_signal.py`** (`classify_demand`) — the **demand** brain. Scores construction/opening
  language the procurement brain rejects by design: facility (hotel / senior-living / student-housing /
  healthcare / correctional / shelter) × project stage (breaks ground / PIP / opening) × bed-count, and
  derives an **estimated buy-window** (when FF&E/mattresses get ordered). Returns ACCEPT/REVIEW/REJECT +
  segment + scale + buy-window.

### Stage 4 — Route (where things land)
| Verdict | Procurement lane → | Demand lane → |
|---|---|---|
| ACCEPT | candidate for `bids/active/_pipeline.csv` (**human-gated**) | `leads/demand/_demand_radar.csv` |
| REVIEW | `leads/review/_lead_radar.csv` (watch list) | `leads/demand/_demand_radar.csv` |
| REJECT | dropped → `logs/rejects/` (audit trail) | dropped → reject log |

> **Hard rule:** nothing enters `bids/active/_pipeline.csv` automatically. A confirmed product-fit bid is
> promoted by a human (`tools/lead_radar.py promote`, then `tools/promote_draft.py` for draft→active).
> The active pipeline stays clean and real.

### Stage 5 — Rank (the Win Engine)
- **`tools/win_score.py`** — `win_score = product_fit × value_tier × win_probability × strategic_fit`
  (0–100). `product_fit` = relevance confidence; weights **value** (bed-count/$), **win-probability**
  (in-region, incumbent, structural blockers), **strategic fit** (home region, correctional/dorm,
  recurring). Brand-restricted (Norix/Purple), blocked-federal (SAM not Active), past-due, and
  out-of-region items **sink toward 0**; in-region mattress/correctional and recurring co-op vehicles
  **rise**. It's the SORT key for lists/digest/email.
- **`tools/readiness.py`** + `configs/capabilities.json` — maps each opportunity's *requirements*
  (SAM Active? 16 CFR 1633 / TB 117? brand authorization? GPO eligibility? bonding?) against our
  *capabilities*, writes the gate columns (`gate_status`/`procurement_risk`/`compliance_blocker`), and
  produces a **"fix-this-to-unlock-the-most-pipeline" backlog** (SAM is #1 — it gates all three recurring
  federal channels: VA/VHA, BOP, Army/DoD barracks).

### Stage 6 — Surface (how it reaches you)
- **`tools/notify_push.py`** — the email digest, sorted by **win_score**, with three clearly-separated
  sections: **Active bid fits**, **Lead Radar**, **Demand Radar (upcoming buy-windows)**.
- **`tools/dashboard.py`** — at-a-glance state (top opportunities by win_score, counts, risks).
- **`.github/workflows/procurement_digest.yml`** — the scheduled digest that also runs the **re-bid prep
  calendar** (`lead_radar.py calendar`) and the **readiness backlog**.

### Stage 7 — Act (the human + helpers)
- **Bids:** `tools/draft_bid_response.py`, `tools/generate_procurement_packet.py`; `tools/validate_vendor_profile.py`
  checks the legal identity/profile is correct before submitting.
- **Re-bid positioning:** `lead_radar.py calendar --emit` → dated **prep windows** (expiry − lead-time)
  with a 5-step checklist; push to Google Calendar (operator/assistant MCP step).
- **Private demand:** `tools/demand_radar.py outreach <id>` → marks a signal for sales contact.

## 3. Data stores (the system's memory)
| File | Lane | Meaning |
|---|---|---|
| `bids/active/_pipeline.csv` | procurement | **Confirmed, biddable** product-fit bids (human-promoted only); carries `win_score` + gate columns |
| `bids/archive/_pipeline_archive.csv` | procurement | No-bid decisions + history |
| `leads/review/_lead_radar.csv` | procurement | Watch list — broad/co-op/recurring signals, 2027–2031 re-bid windows, buyer contacts |
| `leads/demand/_demand_radar.csv` | demand | Pre-RFP private signals, keyed by estimated buy-window, with an `outreach` lifecycle |
| `logs/rejects/` | both | Audit trail of rejected items — so misses are visible, not just hits |
| `configs/feeds.json` | both | Feed list (`kind` flag selects the lane) |
| `configs/capabilities.json` | win | Eligibility matrix (SAM / certs / brands / GPO) |

## 4. Reliability layer ("no news = genuinely no opportunities")
- **RSS feed failures exit non-zero** → the `if: failure()` alert fires (a dead feed used to pass green
  with zero rows — that's how the ~90-fit Bernalillo RFB was missed).
- **Reject logs** (`logs/rejects/`) make misclassifications reviewable.
- **SAM 429 throttle** is distinct from "empty week" (retry + `SAM THROTTLED` marker).
- **`tools/email_watchdog.py`** — alerts if the email channel goes silent (broken-forward detection).
- **`tools/workflow_check.py`** — CI gate: data integrity (future dates, posted>due, score ranges) **and**
  governance (ERROR if a row is biddable while a compliance blocker is open).
- **`tools/pii_lint.py`** + the machine-path leak check — keep PII/secrets out of the repo.

## 5. Automation (GitHub Actions, on cron)
| Workflow | Role |
|---|---|
| `daily_email_ingest.yml` | daily IMAP pull → triage → digest |
| `weekly_rss_ingest.yml` / `weekly_sam_ingest.yml` | RSS + SAM sweeps |
| `weekly_email_ingest.yml` | Graph fallback path for the email channel |
| `procurement_digest.yml` | assemble + email the digest (bids + leads + demand + calendar + readiness) |
| `email_watchdog.yml` | dead-channel detection |
| `ci.yml` | tests + leak/PII checks + `workflow_check` |
| `cleanup_auto_branches.yml` | hygiene |

Ingest runs that find something open a **PR** (human-reviewed) rather than writing straight to `main`.

## 6. Where the human sits in the loop (assistive, not autonomous)
Two gates stay with the operator:
1. **Promotion to the active bid pipeline** — confirm a real product-fit bid (`lead_radar.py promote`).
2. **Outreach on private demand** — choose which Demand Radar signals get a sales call
   (`demand_radar.py outreach`).
Everything upstream (find → classify → rank → position → alert) is automated.

## 7. Live vs. needs setup
- **Live now:** public procurement lane (RSS + SAM + email), relevance classification, Lead Radar,
  win-ranking, readiness, digest, reliability alerts.
- **Built, needs operator switch:** the **Demand Radar** engine + routing + surfacing are merged, but
  there are **no demand feeds yet** — create the Google Alerts per
  [`demand_radar_feed_setup.md`](demand_radar_feed_setup.md), then the URLs get wired into `feeds.json`
  with `kind:"demand"`. That's the one switch to flip the private half on.
- **Optional next builds:** municipal permit open-data adapter (earliest free private signal),
  construction-data email alerts (paid), incumbent/award-intel capture, buyer CRM.

## 8. Mental model
**Two lanes, one ranked funnel, two human gates.** The public lane = *who's buying now*; the demand lane
= *who'll buy soon*; the Win Engine = *which can I win*; readiness = *what's blocking me*; the reliability
layer = *if it's quiet, it's genuinely quiet*.

---

### Tool index (quick reference)
- **Ingest:** `ingest_rss.py` · `ingest_sam.py` · `ingest_email.py` · `ingest_portal_csv.py` (+`portal_csv_mapping.py`)
- **Classify:** `relevance.py` (procurement) · `demand_signal.py` (demand)
- **Stores/CLIs:** `pipeline.py` (bids) · `lead_radar.py` (watch + calendar) · `demand_radar.py` (private)
- **Rank/eligibility:** `win_score.py` · `readiness.py`
- **Surface:** `notify_push.py` · `dashboard.py`
- **Act:** `draft_bid_response.py` · `generate_procurement_packet.py` · `promote_draft.py` · `validate_vendor_profile.py`
- **Reliability/governance:** `workflow_check.py` · `email_watchdog.py` · `pii_lint.py` · `source_review.py`

### Scope note
Living doc — update it when components change. PII (EIN, taxpayer #, banking, street address) stays out of
version control; the SAM UEI is public.
