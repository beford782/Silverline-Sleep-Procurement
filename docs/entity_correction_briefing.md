# Briefing: The "L.P. vs LLC" Legal-Entity Correction — Continental Silverline

> **Purpose:** a self-contained briefing to bring any assistant (human or AI) up to speed on the
> entity-name correction effort with zero prior context. Companion to the actionable
> [`entity_correction_checklist.md`](entity_correction_checklist.md).
> **Last updated:** 2026-06-28.

## 1. The core problem in one sentence
The company's procurement records — across the repo, SAM.gov, and various vendor portals — were built
around a legal entity name that **does not exist** (`CONTINENTAL SILVERLINE PRODUCTS, L.P.`). The only
real, legally-formed entity is **`CONTINENTAL SILVERLINE PRODUCTS, LLC`**, and everything needs to be
reconciled to that.

## 2. The authoritative correct entity (use these values everywhere)
Confirmed against the **Texas Comptroller public record** (operator-confirmed 2026-06-27):

| Field | Correct value |
|---|---|
| Legal name | **CONTINENTAL SILVERLINE PRODUCTS, LLC** |
| Entity type | **Texas Limited Liability Company** (not L.P., not a corporation) |
| State of formation | Texas |
| Formed / start year | **2015** (effective SOS registration 12/31/2015) |
| Texas SOS file number | **0802357166** (public) |
| Registered agent | **C T Corporation System**, 1999 Bryan St Ste 900, Dallas, TX 75201 |
| Physical address | 710 N Drennan St, Houston, TX 77003-1321 |
| SAM.gov UEI (current, WRONG-named) | **XF73FG8CVMX1** (public) |
| EIN / Texas Taxpayer Number | **[on file — PII, never put in version control or share with an AI]** |

**There is NO L.P. entity.** It was always a clerical mistake. The LLC is the only real entity.

## 3. Critical scoping fact (limits the blast radius)
The operator clarified 2026-06-27:
- **The W-9 submitted to portals is already correct** — it lists "Continental Silverline Products, LLC,"
  not L.P.
- Therefore the **EIN is correct everywhere** → there is **NO** wrong-EIN / 1099 / payment-mismatch
  problem, and **no accountant is needed for the portal fixes.**
- What's actually wrong is mostly: (a) the **repo's own records** (now fixed), and (b) **stray "legal
  name" display fields** that were typed as "L.P." in some portal vendor profiles. Those are
  **name-only text corrections** — no EIN involved.

So the work splits cleanly:
- **Name-only fixes** (collaborative: operator logs in, assistant edits the name field) — most portals.
- **Anything touching EIN / W-9 / banking** (operator or accountant only) — SAM banking, master W-9.

## 4. What's already been fixed (repo)
The repo previously asserted "L.P." as canonical. That's been corrected:
- Corrected legal entity to LLC across the repo (`docs/company_identity.md`, SAM runbook).
- Entity-correction master checklist + cleanup.
- The master checklist at [`entity_correction_checklist.md`](entity_correction_checklist.md) tiers every
  record that carries the entity name (master / federal / payment-portals / name-only-portals / verify).

## 5. What was VERIFIED on 2026-06-28 (browser, logged in)

### SAM.gov -> confirmed WRONG (shows L.P.)
Logged into SAM.gov. The entity registration **displays `CONTINENTAL SILVERLINE PRODUCTS, L.P.`**:
- Status: **Work-In-Progress** (not submitted, not Active)
- UEI: XF73FG8CVMX1 - CAGE: none - **Banking: not entered**

This resolved a previously-open question (we weren't sure whether SAM had used L.P. or LLC). It used
L.P. -> **needs correction.**
**Hard rule now:** do **NOT** complete SAM Financial/EFT banking and do **NOT** cite this UEI on bids
until the name is fixed. A **PII-free FSD ticket draft** is saved at
[`sam_fsd_entity_correction_ticket.md`](sam_fsd_entity_correction_ticket.md).

### NM-SPD / Euna (Bonfire) -> confirmed CORRECT (already LLC)
Logged into Euna Supplier Network. **No "L.P." anywhere.** Euna is a single network account; its Business
Profile reads "Continental Silverline LLC" and propagates to all Bonfire tenants (including NM-SPD) —
there's no separate per-tenant legal-name field to fix. Mattress commodity coverage confirmed
(UNSPSC 56.10.15.08 "Mattresses or sleep sets" + 42.19.18.10 "Patient care mattresses"; keywords
bedding/mattress/mattresses). The old "submitted as L.P." worry was a leftover from the wrong-entity
session. **Nothing to fix here.**

## 6. SAM.gov mechanics to understand (the genuinely tricky part)
- In SAM, the **legal business name is bound to the UEI via "Entity Validation"** (a contractor-run match
  against authoritative records). You generally **cannot freely edit the legal name** of an existing UEI.
- SAM also validates **legal name + EIN against the IRS**. If "L.P." was entered against the **LLC's**
  EIN, that IRS match would likely **fail** — so this WIP registration may be a dead end regardless.
- UEI is designed **one-per-entity-per-address**. The wrong record and the LLC share the same address
  (710 N Drennan St), which creates a real risk of **duplicate-entity conflicts** if a second
  registration is attempted.

**Two candidate paths (do ONE, not both in parallel):**
1. **Self-service first (faster, reversible):** "Register New Entity" -> run Entity Validation as
   "CONTINENTAL SILVERLINE PRODUCTS, LLC." A WIP registration isn't binding. If it cleanly assigns a new
   UEI -> proceed. If it conflicts/duplicates -> escalate.
2. **FSD ticket (fallback):** fsd.gov / 866-606-8220 — ask whether the name on UEI XF73FG8CVMX1 can be
   corrected vs. needing fresh validation + new UEI, and how to retire the L.P. record. Draft ready in the
   repo.

The **EIN/banking entry is operator/accountant-only** — an AI must not type tax IDs, passwords, or
banking details.

## 7. What remains (open work)
From [`entity_correction_checklist.md`](entity_correction_checklist.md):
- **Tier 0 (master records):** confirm LLC on master W-9, insurance COIs, TX sales-tax permit, DBA filings
  (Restonic / Spring Air / Silverline Sleep), customer-facing docs, existing contracts/POs.
- **Tier 1 (SAM):** the validation/FSD path above. *Next action.*
- **Tier 2 (payment portals — operator, EIN/W-9):** Oklahoma OMES, Louisiana OSP/LaGov, Mississippi MAGIC,
  Arkansas ARBuy, New Orleans, East Baton Rouge, Bexar County.
- **Tier 3 (name-only edits — collaborative):** City of Houston/Beacon, TIPS, EPIC6, Region 4/OMNIA, E&I,
  Sourcewell, El Paso County, Tarrant County, Dallas County/BidNet (six-state), Texas A&M, OU, OSU,
  LSU/LaPAC. *(NM-SPD already verified done.)*
- **Tier 4 (verify):** Texas CMBL (the canonical record everything reconciles to), TX ESBD/SmartBuy,
  Walker County, Choice Partners/HCDE, BuyBoard.

## 8. Operating constraints any assistant must respect
- **PII never enters version control or AI chat:** EIN, Texas Taxpayer Number, banking, street address.
  (UEI and SOS file number are public, OK to use.)
- An AI is **prohibited** from entering tax IDs, passwords, or banking — operator does those.
- Repo workflow: **one PR per change, branch off main, return to clean main.** No PII in commits.

## 9. Key files
- [`entity_correction_checklist.md`](entity_correction_checklist.md) — the master tiered checklist
- [`sam_fsd_entity_correction_ticket.md`](sam_fsd_entity_correction_ticket.md) — PII-free FSD ticket draft
- [`company_identity.md`](company_identity.md) — canonical identity record (corrected to LLC)
- [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md) — full
  rationale + per-portal URLs

---

**One caution:** treat the *correctness* of each portal as **unverified until someone logs in and looks**
— the repo's own historical notes were the source of the original error, so don't trust a label without
confirming the live display. (That's exactly how, on 2026-06-28, we found SAM was wrong but NM was already
fine.)
