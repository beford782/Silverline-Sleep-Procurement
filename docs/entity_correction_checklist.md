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
| [~] | **SAM.gov** | **VERIFIED 2026-06-28: registration displays `CONTINENTAL SILVERLINE PRODUCTS, L.P.` (wrong), status Work-In-Progress, UEI `XF73FG8CVMX1`, no CAGE, no banking entered.** **Do NOT complete banking. Do NOT cite UEI `XF73FG8CVMX1`.** Next step (drafted): file an FSD ticket (fsd.gov / 866-606-8220) — see [`sam_fsd_entity_correction_ticket.md`](sam_fsd_entity_correction_ticket.md) — to ask whether the legal name on this UEI can be corrected to the LLC, or whether a fresh entity validation / new UEI is required. Either way, register/finish as the **LLC** under its own EIN. | Blake + accountant |

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
| [x] | **NM-SPD Euna/Bonfire tenant** | Euna/Bonfire | **VERIFIED 2026-06-28: no L.P. anywhere — Euna Supplier Network is a single network account; Business Profile reads "Continental Silverline LLC" and propagates to all tenants incl. NM-SPD. The old "submitted as L.P." note was a leftover from the wrong-entity session. Keywords (bedding/mattress/mattresses) + UNSPSC mattress codes (56.10.15.08, 42.19.18.10) set. Minor open watch: whether NM-SPD needs an explicit per-tenant "follow" beyond network membership.** |
| [ ] | **City of Houston** | Beacon Bid | Home city — NOT yet checked |
| [x] | **TIPS** (Region 8) | IonWave | **VERIFIED 2026-06-28: no L.P.** Org Type = "Limited Liability Company"; Trade Name "Continental Silverline", Legal Name blank; UEI field blank. IonWave uses ONE shared profile at `supplier.ionwave.net` (see note below). |
| [x] | **EPIC6 / Region 6** | IonWave | **VERIFIED 2026-06-28 (via shared IonWave profile)** — same record as TIPS/Region 4; Org Type = LLC, no L.P. |
| [x] | **Region 4 ESC / OMNIA** | IonWave | **VERIFIED 2026-06-28: no L.P.** Opened the identical `supplier.ionwave.net` profile as TIPS; Org Type = LLC. |
| [x] | **E&I Cooperative** | JAGGAER | **VERIFIED 2026-06-28: no L.P.** Legal Company Name "Continental Silverline"; Legal Structure = Single-Member LLC. Shares JAGGAER Supplier Network profile supplierID 1011150392 (see note). |
| [ ] | **Sourcewell** | Sourcewell portal | NOT yet checked (separate platform) |
| [x] | **El Paso County** | IonWave | **VERIFIED 2026-06-28 (via shared IonWave profile)** — Org Type = LLC, no L.P. |
| [x] | **Tarrant County** | IonWave | **VERIFIED 2026-06-28 (via shared IonWave profile)** — Org Type = LLC, no L.P. |
| [x] | **Dallas County / BidNet Direct** (six-state profile) | BidNet | **VERIFIED 2026-06-28: no L.P.** Org Name = brand "Silverline Sleep"; Business Structure = "LLC or LLP". One profile across all six states. Also fixed a stale org-contact email (restonichouston → silverlinesleep); alert routing already correct (user Preferences email = silverlinesleep). |
| [x] | **Texas A&M (AggieBid)** | JAGGAER | **VERIFIED 2026-06-28: no L.P.** Legal Company Name "Continental Silverline"; Single-Member LLC. Shared JAGGAER profile supplierID 1011150392. |
| [x] | **University of Oklahoma** (OUHSC) | JAGGAER | **VERIFIED 2026-06-28 (via shared JAGGAER profile)** — same supplierID 1011150392; Single-Member LLC, no L.P. |
| [x] | **Oklahoma State University** | JAGGAER | **VERIFIED 2026-06-28 (via shared JAGGAER profile)** — same supplierID 1011150392; no separate record. |
| [ ] | **LSU / LaPAC** enrollment | LaPAC | NOT yet checked (ties to LA OSP / LaGov — payment-capable) |

> **Key 2026-06-28 sweep discovery — unified supplier profiles:** IonWave portals all read ONE company
> profile at `supplier.ionwave.net` (Org Type = Limited Liability Company), and JAGGAER portals (E&I,
> TAMU, OU, OSU) all share ONE JAGGAER Supplier Network profile, supplierID **1011150392** (Legal
> Structure = Single-Member LLC). So a single check per platform covers every portal on it. **Across
> every live portal checked — BidNet, all IonWave, all JAGGAER, NM/Euna — there was NO "L.P." anywhere;
> all already read as LLC.** This confirms the "L.P." problem was the repo's own records + the single
> SAM.gov record, not the live registrations. Names are recorded as the brand ("Continental Silverline" /
> "Silverline Sleep") with structure = LLC and the LLC's EIN — making the full "…PRODUCTS, LLC" exact is
> an optional cosmetic, not an L.P. fix. Remaining unchecked: City of Houston, Sourcewell, LSU/LaPAC, and
> the Tier-2 payment-capable portals (operator/accountant taxpayer-name eyeball).

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
