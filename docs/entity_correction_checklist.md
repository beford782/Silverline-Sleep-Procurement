# Entity Correction Master Checklist — L.P. → LLC

- **Goal:** change every record that says **CONTINENTAL SILVERLINE PRODUCTS, L.P.** to the only real
  entity: **CONTINENTAL SILVERLINE PRODUCTS, LLC** (Texas LLC, SOS file **0802357166**, formed
  **2015**, its **own EIN/taxpayer number**). There is no L.P. — it was always a mistake.
- **Correct values to use:** legal name `CONTINENTAL SILVERLINE PRODUCTS, LLC`; entity type **Texas
  Limited Liability Company**; state **TX**; start year **2015**; SOS file **0802357166**; registered
  agent **C T Corporation System** (Dallas, TX). EIN / Texas Taxpayer Number = **[from your records — never typed by Claude]**.
- **Status legend:** `[ ]` to do · `[~]` in progress · `[x]` done.
- **Who can do it:**
  - **Blake-only** — needs your login + your EIN/W-9/banking (Claude is prohibited from entering tax IDs, passwords, or banking).
  - **Blake + Claude** — name-only text edit: *you* log in, *Claude* makes the edit (pauses before save).
  - **Accountant** — IRS/EIN/tax-name reconciliation or legal novation.

> **Order matters:** do **Tier 0** (the master records that propagate) and **Tier 1 (SAM)** first.
> Then we run **Tier 3** together (you log in, I edit). Tier 2 is yours because of the EIN/W-9.

---

## TIER 0 — Master records (do FIRST; they propagate everywhere)
| ☐ | Record | What to change | Who |
|---|---|---|---|
| [ ] | **Master W-9** | Reissue as the LLC with the LLC's EIN. *Every buyer uses this — highest propagation.* | Accountant / Blake |
| [ ] | **IRS / EIN** | Confirm the LLC's own EIN is the one used everywhere; reconcile taxpayer name (CP-575 / 147C). | Accountant |
| [ ] | **Business bank account** | Confirm the account is in the LLC's legal name (SAM's EFT pulls from this). | Blake |
| [ ] | **Insurance COIs** (GL / product liability) | Named insured = the LLC; get updated certificates. | Blake / agent |
| [ ] | **TX tax permits** (sales/use, franchise) | Comptroller already shows LLC ✅; verify the sales-tax permit reads LLC. | Blake |
| [ ] | **DBA / assumed-name filings** (Restonic / Spring Air / Silverline Sleep) | Confirm filed under the LLC. | Blake |
| [ ] | **Customer-facing docs** | Capability statement (repo ✅), line cards, quotes, invoices, letterhead, email signature, website footer → LLC. | Blake |
| [ ] | **Existing contracts / POs / awards** under a wrong name | Flag for correction/novation. | Blake / legal |

## TIER 1 — Federal (STOP, then re-register)
| ☐ | Record | What to change | Who |
|---|---|---|---|
| [ ] | **SAM.gov** | **Do NOT complete banking. Do NOT cite UEI `XF73FG8CVMX1`.** Open an FSD ticket (fsd.gov / 866-606-8220); register the **LLC fresh** under its own EIN → new UEI + CAGE. | Blake + accountant |

## TIER 2 — Payment-capable portals (correct name **and** resubmit LLC W-9/EIN)
*Claude can't do these — they require the EIN/W-9.*
| ☐ | Portal | ID on file | Who |
|---|---|---|---|
| [ ] | **Oklahoma OMES** Supplier Portal | Reg ID 0000018606 | Blake |
| [ ] | **Louisiana OSP / LaGov** SUS (also fixes LSU/LaPAC downstream) | — | Blake |
| [ ] | **Mississippi DFA / MAGIC** SUS | — | Blake |
| [ ] | **Arkansas OSP / ARBuy** (Periscope/BSO) | — | Blake |
| [ ] | **New Orleans / Orleans Parish** (BRASS-Infor) | Supplier 13390 | Blake |
| [ ] | **East Baton Rouge** / Central Bidding | Vendor 1099 (reconcile dup email) | Blake |
| [ ] | **Bexar County** (Infor) | Supplier 17427 | Blake |

## TIER 3 — Name-only portal edits (you log in, Claude edits)
*These have no EIN/W-9 field — once you're logged in, Claude changes the legal name.*
| ☐ | Portal | Platform | Notes |
|---|---|---|---|
| [ ] | **NM-SPD Euna/Bonfire tenant** | Euna/Bonfire | Submitted as L.P. this session; verify vs the (correct) Euna parent profile |
| [ ] | **City of Houston** | Beacon Bid | Home city |
| [ ] | **TIPS** (Region 8) | IonWave | |
| [ ] | **EPIC6 / Region 6** | IonWave | |
| [ ] | **Region 4 ESC / OMNIA** | IonWave | |
| [ ] | **E&I Cooperative** | JAGGAER | |
| [ ] | **Sourcewell** | Sourcewell portal | |
| [ ] | **El Paso County** | IonWave | |
| [ ] | **Tarrant County** | IonWave | |
| [ ] | **Dallas County / BidNet Direct** (six-state profile) | BidNet | One profile propagates across the 6-state aggregation |
| [ ] | **Texas A&M (AggieBid)** | JAGGAER | |
| [ ] | **University of Oklahoma** (OUHSC) | JAGGAER | |
| [ ] | **Oklahoma State University** | JAGGAER | |
| [ ] | **LSU / LaPAC** enrollment | LaPAC | May update with the LA OSP fix |

## TIER 4 — Verify, or register fresh as LLC
| ☐ | Record | Action | Who |
|---|---|---|---|
| [ ] | **Texas CMBL** | Verify it reads LLC + LLC taxpayer # (the canonical record everything reconciles to) | Blake |
| [ ] | **Texas ESBD / SmartBuy** | Verify no stray L.P. display name (inherits CMBL) | Blake / Claude |
| [ ] | **Walker County** (Bonfire) | Confirm whether a vendor profile exists vs RSS-only | Blake / Claude |
| [ ] | **Choice Partners / HCDE** | Register **fresh as LLC** (was UEI-gated; ignore old L.P. fields) | Blake + Claude |
| [ ] | **BuyBoard (TASB)** | Register **fresh as LLC** | Blake + Claude |
| [x] | **Euna Supplier Network PARENT profile** | Already "Continental Silverline LLC" — **DO NOT change.** Verify only. | — |

---

### Notes
- This list = everything the repo tracks (the registration ledger) + the non-portal records that carry
  the entity name. If you registered anywhere **not** logged here, add a row — the
  `portal_registration_tracker.csv` was never populated, so the ledger is the best (not guaranteed
  exhaustive) record.
- Full rationale + per-portal URLs: [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md).
- PII rule: EIN / taxpayer number / banking never go in this repo.
