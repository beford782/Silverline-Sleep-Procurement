# Entity Correction Walkthrough — L.P. → LLC across every online location

- **For:** Blake / Continental Silverline Products, LLC (Houston, TX)
- **Date:** 2026-06-28
- **What this is:** the execution playbook for correcting the wrong legal name
  **`CONTINENTAL SILVERLINE PRODUCTS, L.P.`** → **`CONTINENTAL SILVERLINE PRODUCTS, LLC`**
  in every online vendor/procurement location (plus the foundational records they depend on).
  Built from the tiered [`entity_correction_checklist.md`](entity_correction_checklist.md);
  this doc adds the *per-platform steps, who-does-what, and the order to do them in*.

> Companion docs: [`entity_correction_briefing.md`](entity_correction_briefing.md) (the why),
> [`entity_correction_checklist.md`](entity_correction_checklist.md) (the tiered list),
> [`sam_fsd_entity_correction_ticket.md`](sam_fsd_entity_correction_ticket.md) (the SAM ticket).

---

## Read this first — the rules that shape everything below

1. **Correct values:** legal name `CONTINENTAL SILVERLINE PRODUCTS, LLC`; entity type **Texas
   Limited Liability Company**; state **TX**; start year **2015**; SOS file **0802357166**;
   registered agent **C T Corporation System** (Dallas, TX). There is **no L.P.** — it was always a mistake.

2. **The blast radius is small — most fixes are NAME-ONLY.** The **W-9/EIN already submitted to
   portals is correct (the LLC's)**, so for the large majority of portals this is a **display-name
   correction only** — log in, change the company/legal-name field, no EIN/W-9 resubmission.

3. **Three execution modes** (every location is tagged with one):
   - 🟢 **NAME-ONLY (collaborative):** Blake logs in, **Claude edits** the legal-name field and
     **pauses before Save**. No tax field involved.
   - 🟡 **PAYMENT-CAPABLE (operator/accountant):** the portal stores a taxpayer name / W-9 / banking.
     **Blake (or accountant) only** — Claude must **never** enter or view EIN, tax IDs, or banking.
     The task is usually *verify the taxpayer name already reads LLC*, not re-enter it.
   - 🔵 **VERIFY-ONLY:** already correct or inherits from another record — **confirm, do not change.**

4. **"Current name is UNVERIFIED" — check, then change.** The repo only ever confirmed L.P. on
   **SAM.gov**. Everywhere else, the step is *"log in, read the legal-name field, change it only if
   it shows L.P."* Do not assume L.P. is showing.

5. **Two hard prohibitions, everywhere:**
   - **Never type SAM UEI `XF73FG8CVMX1`** into any portal — it's on the blocked wrong-named SAM
     record. If a UEI field is *optional* → leave blank; if *required* → pause that portal.
   - **PII never appears here or in chat:** EIN, taxpayer number, CMBL number, phone, street
     address, banking → `[on file]`, operator/accountant-only.

---

## Master location table

| # | Location | Platform | Mode | Who | EIN/W-9? | Priority |
|---|---|---|---|---|---|---|
| **Foundational / federal** | | | | | | |
| F1 | **Master W-9** | — | 🟡 | Accountant/Blake | YES | **Now (parallel)** |
| F2 | **IRS / EIN taxpayer-name** | — | 🟡 | Accountant | YES | Now (parallel) |
| F3 | **Business bank account name** | — | 🟡 | Blake | YES (name) | Now (parallel) |
| F4 | **Insurance COIs (GL/product)** | — | 🟡 | Blake/agent | NO (named insured) | Now (parallel) |
| F5 | **TX tax permits (sales/franchise)** | Comptroller | 🟡 | Blake | YES | Now (parallel) |
| F6 | **DBA filings** (Restonic/Spring Air/Silverline Sleep) | County clerk | 🟡 | Blake | NO | Now (parallel) |
| F7 | **Customer-facing docs** (cap statement, quotes, invoices, letterhead, website) | — | 🟢/🟡 | Blake (repo: Claude) | NO | Now (parallel) |
| F8 | **Existing contracts / POs / awards** under a wrong name | — | 🟡 | Blake/legal | NO | Now (parallel) |
| S1 | **SAM.gov** (federal) | SAM.gov | 🟡 special | Blake+accountant | YES | **The federal blocker — see §SAM** |
| **Texas master** | | | | | | |
| T1 | **Texas CMBL** (canonical) | Comptroller eSystems | 🟡 | Blake (carries taxpayer #) | YES | **Highest TX priority** |
| T2 | **Texas ESBD / SmartBuy** | ESBD | 🔵 inherits CMBL | Blake/Claude | NO | After CMBL |
| **High-propagation name-only** | | | | | | |
| N1 | **BidNet Direct** six-state (TX/LA/AR/MS/NM/OK) | BidNet | 🟢 | Blake+Claude | NO | **One edit covers 6 states** |
| **Co-ops / counties (IonWave)** | | | | | | |
| I1 | **TIPS** (Region 8 ESC) | IonWave | 🟢 | Blake+Claude | NO | High (furniture re-bid nearest) |
| I2 | **Region 4 ESC / OMNIA** | IonWave | 🟢 | Blake+Claude | NO | High (OMNIA gateway) |
| I3 | **EPIC6 / Region 6 ESC** | IonWave | 🟢 | Blake+Claude | NO | Med |
| I4 | **El Paso County** | IonWave | 🟢 | Blake+Claude | NO | Med |
| I5 | **Tarrant County** | IonWave | 🟢 | Blake+Claude | NO | Med |
| I6 | **Arkansas IonWave / AR Bid** (Pulaski Co.) | IonWave | 🟢 (confirm acct exists) | Blake+Claude | NO | Med |
| I7 | **Choice Partners / HCDE** | IonWave | ⏸ UEI-gated | Blake+Claude | NO | **After SAM** |
| I8 | **BuyBoard (TASB)** | IonWave | ⏸ UEI-gated / register fresh | Blake+Claude | NO | **After SAM** |
| **Higher-ed / E&I (JAGGAER/SciQuest)** | | | | | | |
| J1 | **E&I Cooperative** | JAGGAER | 🟢 (verify tax section) | Blake+Claude | maybe | High (live mattress contract) |
| J2 | **Oklahoma State Univ (OSU)** | JAGGAER/SciQuest | 🟢 | Blake+Claude | NO | Med (full onboarding done) |
| J3 | **University of Oklahoma (OUHSC)** | JAGGAER/SciQuest | 🟢 | Blake+Claude | NO | Med |
| J4 | **Texas A&M (AggieBid)** | JAGGAER/SciQuest | 🟢 | Blake+Claude | NO | Med |
| J5 | **New Mexico eProNM** (legacy) | SciQuest/JAGGAER | 🔵 verify/skip | Blake | NO | Low (being retired) |
| **Payment-capable state + Infor** | | | | | | |
| P1 | **New Orleans BRASS** (supplier 13390) | Infor | 🟡 | Blake/accountant | YES | High (completed profile) |
| P2 | **Bexar County** (supplier 17427) | Infor | 🟡 | Blake/accountant | YES | High |
| P3 | **East Baton Rouge VSS** (vendor 1099) | VSS/Central Bidding | 🟡 | Blake/accountant | YES | High (+ dup-email fix) |
| P4 | **Louisiana LaGov SUS** | SAP SUS | 🟡 | Blake/accountant | YES | Med (propagates to LaPAC/LSU) |
| P5 | **Mississippi MAGIC SUS** | SAP SUS | 🟡 | Blake/accountant | YES | Med |
| P6 | **Arkansas ARBuy** (Periscope/BSO) | BSO | 🟡 | Blake/accountant | YES | Med |
| P7 | **Oklahoma OMES** (Reg 0000018606) | OMES portal | 🟡 | Blake/accountant | maybe | Low (payment setup may be deferred) |
| **City / Bonfire / Euna** | | | | | | |
| C1 | **City of Houston** | Beacon Bid / SAP Business Network | 🟢 | Blake+Claude | NO | Med (home city) |
| B1 | **Walker County** | Bonfire/Euna | 🔵 confirm profile vs RSS | Blake | NO | Low |
| B2 | **Bernalillo County** | Bonfire/Euna | 🔵 confirm profile vs RSS | Blake | NO | Low |
| V1 | **NM-SPD Euna/Bonfire tenant** | Euna/Bonfire | 🔵 **verified correct 2026-06-28** | — | NO | Confirm only |
| V2 | **Euna Supplier Network parent** | Euna | 🔵 **already "Continental Silverline LLC"** | — | NO | **Do NOT change** |

---

## Per-platform "how to reach the legal-name field"

Steps repeat within a platform — learn the path once, apply across that platform's portals.

### IonWave (TIPS, Region 4/OMNIA, EPIC6, El Paso, Tarrant, Arkansas, HCDE, BuyBoard)
Log in → top-right account / **"My Account"** or **"Vendor Profile"** → **"Company Information"**
(sometimes "Company Info" / "Preliminary Company Information") → **Company/Legal Name** field →
if it reads "…, L.P." change to "…, LLC"; set entity type **Limited Liability Company** if shown →
**Save**. Exact label varies by tenant — *confirm in-portal*. **Notification email** stays
`beford@silverlinesleep.com`. **UEI field:** optional → blank; required → pause (never type `XF73FG8CVMX1`).

### JAGGAER / SciQuest (E&I, OSU, OU, AggieBid, eProNM)
Log in from the customer's sourcing board (or supplier portal) → account menu → **"Manage
Registration Profile"** → **Company Overview / Business Details → "Legal Company Name"** → change
L.P. → LLC → **Save, then re-Certify/Submit that section** (JAGGAER often needs the section
re-submitted, not just saved). **Two cautions:** (a) the legal-name field is sometimes **locked**
(tied to tax/validation) — if greyed out, email that customer's supplier-relations team to request
the change (OU: `SupplierRelations@ou.edu`); (b) each customer is a **separate profile** — no
cross-propagation, repeat per portal. For **E&I**, also glance at any Tax/W-9 section and confirm
the taxpayer name reads LLC (operator-only) — don't re-enter EIN.

### Infor Supplier Portal (New Orleans BRASS, Bexar County) — 🟡 operator/accountant
Log in → **Supplier Profile / Company Information** (display name) **and** the **Tax Information /
Remittance (W-9 / taxpayer name)** tab. **Blake/accountant** verifies the **taxpayer name reads
LLC**; resubmit the LLC W-9 / correct the taxpayer name **only if** it shows L.P. These completed
profiles are the **likeliest place a taxpayer name persists as L.P.** — check them carefully.

### State Supplier Self-Service (LaGov SUS, Mississippi MAGIC, Arkansas ARBuy/BSO, Oklahoma OMES) — 🟡
Log in → **Company Data / General Data** (display legal name) **and** the **Tax / W-9 / TIN**
section. **Blake/accountant** verifies the **taxpayer name = LLC**; resubmit LLC W-9 only if it
shows L.P. Note: for several of these the *payment/tax step may have been deferred* at registration —
*confirm in-portal whether a tax record even exists yet*. **LaGov is high-leverage** — fixing the
name there propagates to **LaPAC and LSU**.

### BidNet Direct (the six-state profile) — 🟢
Log in → **Company Profile** (supplier account) → company/legal-name field → change L.P. → LLC →
**Save**. **One edit covers all six Purchasing Groups** (TX/LA/AR/MS/NM/OK) and downstream local
agencies (e.g., Dallas County). No tax field.

### Bonfire / Euna (NM-SPD, Walker, Bernalillo, parent) — 🔵 mostly verify-only
The legal name comes from the **single Euna Supplier Network Business Profile**, already verified
**"Continental Silverline LLC."** Any Bonfire tenant where Blake holds a logged-in vendor profile
**inherits** that — so these are **confirm-only**. For Walker/Bernalillo, **first determine whether a
vendor profile exists at all vs. RSS-only** (the ledger suggests RSS-only — if so, *nothing to fix*).
**Do not edit the Euna parent or the NM-SPD tenant** (both already correct).

### Texas CMBL (Comptroller eSystems) — 🟡 operator-only, CANONICAL
Blake logs in → CMBL vendor profile → confirm **legal/business name = LLC** and the **taxpayer
number** is the LLC's (taxpayer # is PII — Blake-only, Claude must not view). **Do this first among
Texas records** — ESBD/SmartBuy and other TX systems reconcile to it.

### City of Houston — Beacon Bid / SAP Business Network — 🟢
Log in to the Beacon Bid vendor profile → company/legal-name field. Houston supplier identity is
registered through **SAP Business Network**; if the name is read-only in Beacon Bid, follow through
to the **SAP Business Network company profile** to correct it. *Confirm in-portal which layer holds
the editable name.* No tax-field change (LLC W-9 already correct).

---

## SAM.gov — the federal blocker (decision tree)

**Verified 2026-06-28:** SAM shows a **Work-In-Progress** registration under the wrong name
`CONTINENTAL SILVERLINE PRODUCTS, L.P.`, UEI `XF73FG8CVMX1`, **no CAGE, no banking**. In SAM the
legal name is **bound to the UEI by Entity Validation** and **matched to the IRS** (name+EIN).

**Hard rules:** (1) do **not** complete Financial/EFT banking; (2) do **not** cite `XF73FG8CVMX1`
on any bid; (3) **pick ONE path — never both in parallel** (a second registration at the same
address risks a duplicate-entity conflict); (4) the **EIN/Taxpayer and banking sections are
operator/accountant-only** — Claude can help with name/address/SOS/start-year fields and pauses
before anything touching the TIN.

**Choose the path:**
- **Path (b) — FSD ticket (recommended, conservative):** because the LLC and the L.P. record share
  the same address (710 N Drennan St), there's real duplicate-UEI risk. File the ready draft
  [`sam_fsd_entity_correction_ticket.md`](sam_fsd_entity_correction_ticket.md) at **fsd.gov** or call
  **866-606-8220**. It asks: can `XF73FG8CVMX1` be corrected vs. needs fresh validation/new UEI; how
  to retire the L.P. record; confirm the IRS match runs against the LLC. Have ready: TX SOS formation
  record (file 0802357166), TX Comptroller "Active" record, IRS EIN doc (CP-575/147C).
- **Path (a) — self-service (faster, reversible):** "Register New Entity" → Entity Validation as
  `CONTINENTAL SILVERLINE PRODUCTS, LLC` (street address, **not** a P.O. box; start year 2015; TX;
  SOS 0802357166). **Watch for a duplicate-UEI-at-same-address conflict** — if it flags one, **stop**
  and fall back to (b). **Stop at the Taxpayer/EIN and Financial/EFT sections — Blake/accountant.**

**After a valid LLC UEI exists:** re-point the UEI-gated portals (**HCDE/Choice**, **BuyBoard**) to
it; Blake/accountant completes EFT banking on the correct record → IRS match clears → CAGE issues →
status flips **Active**. Update the SAM row in [`active_registrations.md`](active_registrations.md).

---

## Recommended execution sequence

**Phase 0 — Start now, in parallel (foundational, not blocked by SAM):**
F1 Master W-9 · F2 IRS/EIN taxpayer name · F3 bank account name · F4 insurance COIs · F5 TX tax
permits · F6 DBA filings · F7 customer-facing docs · F8 existing contracts. **T1 Texas CMBL** (anchors
all TX records). *These are mostly "verify it reads LLC," and since the EIN is already correct, the
blast radius is small.*

**Phase 1 — SAM.gov:** pick ONE path (FSD recommended). This unblocks the UEI-gated portals.

**Phase 2 — High-propagation name-only (collaborative, fast):**
N1 BidNet six-state (one edit → 6 states) · then the IonWave sweep in one logged-in session:
I1 TIPS → I2 Region 4/OMNIA → I3 EPIC6 → I4 El Paso → I5 Tarrant → I6 Arkansas IonWave (confirm
account first). Then the JAGGAER sweep (same UI, different CustomerOrg, back-to-back):
J1 E&I → J2 OSU → J3 OU → J4 AggieBid. Then C1 City of Houston/Beacon.

**Phase 3 — Payment-capable EIN verification (Blake/accountant):**
P1 New Orleans BRASS → P2 Bexar → P3 East Baton Rouge (+ reconcile the duplicate vendor email
`beford@restonichouston.com`) → P4 LaGov (propagates to LaPAC/LSU) → P5 MAGIC → P6 ARBuy → P7 OMES.

**Phase 4 — Verify-only confirmations:**
T2 Texas ESBD/SmartBuy (after CMBL) · V1 NM-SPD tenant · V2 Euna parent (**do not change**) ·
B1 Walker / B2 Bernalillo (confirm profile-vs-RSS — likely no action) · J5 eProNM (likely skip).

**Phase 5 — UEI-gated (only after SAM resolves):** I7 HCDE/Choice · I8 BuyBoard (register fresh as LLC).

---

## The collaborative protocol (how Blake + Claude run a 🟢 name-only portal)

1. Blake opens the portal and **logs in** (Claude can pre-fill a known business email but never a
   password).
2. Claude navigates to the company/legal-name field per the platform guide above and **reads it back**.
3. If it shows **L.P.**, Claude edits it to `CONTINENTAL SILVERLINE PRODUCTS, LLC` and **pauses before
   Save** so Blake confirms.
4. Blake clicks Save/Submit (the irreversible action stays with Blake).
5. Record the outcome; Claude updates [`active_registrations.md`](active_registrations.md) +
   [`entity_correction_checklist.md`](entity_correction_checklist.md).

**Stop conditions:** any UEI-required field → pause; any tax/W-9/banking field → hand to Blake/accountant
(🟡); a locked legal-name field → switch to "email that portal's supplier-relations team."

---

### Scope note
Docs only. Per-portal URLs and account IDs are drawn from the committed
[`entity_correction_checklist.md`](entity_correction_checklist.md),
[`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md),
[`active_registrations.md`](active_registrations.md), and `leads/review/_lead_radar.csv`. PII
(EIN, taxpayer number, CMBL #, phone, street address, banking) stays out of version control as `[on file]`.
