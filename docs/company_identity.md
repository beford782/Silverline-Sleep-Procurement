# Company Identity - Canonical Card

- **Purpose:** One authoritative place for the company's legal identity so every
  registration, bid, runbook, and capability statement uses the **same values**.
  When a portal or form asks "what's the legal name / entity type / NAICS," copy
  from here. If any other doc disagrees with this card, **this card wins** - fix
  the other doc.
- **Why this exists:** A serious error was found 2026-06-27 - the entity had been
  recorded everywhere as a *Limited Partnership (L.P.)*. That is WRONG. The
  authoritative Texas Comptroller / SOS record is **CONTINENTAL SILVERLINE
  PRODUCTS, LLC** (a Texas LLC). There is **no L.P.** - it was always a mistake.
  See [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md).

> **PII rule:** values marked `[on file]` - **EIN, Texas Taxpayer Number, CMBL
> number, phone, street address** - are kept **out of version control** (operator
> records only). The legal name, entity type, formation date, SOS file number,
> registered agent, NAICS, and PSC are public and safe to record.

---

## The card

| Field | Value |
|---|---|
| **Legal name** | **CONTINENTAL SILVERLINE PRODUCTS, LLC** |
| **Entity type** | **Texas Limited Liability Company (LLC)** - *not* an L.P., *not* a corporation |
| **Formation doc** | **Certificate of Formation** (a Texas LLC files one) |
| **State of formation** | Texas |
| **Formation / start year** | **2015** (effective SOS registration 12/31/2015) |
| **Texas SOS File Number** | **0802357166** (public) |
| **Registered agent** | **C T Corporation System**, 1999 Bryan St, Ste 900, Dallas, TX 75201 (public) |
| **Status** | Active (Right to Transact Business in TX: Active) |
| **SAM.gov UEI** | **NONE valid yet.** UEI `XF73FG8CVMX1` belongs to the wrong (nonexistent) L.P. and its different EIN - do NOT use it. The LLC needs its OWN new SAM registration + new UEI (see the correction plan / `sam_uei_unblock_runbook.md`). |
| **DUNS** | Deprecated by the federal government (2022) - leave blank; the UEI replaces it. |
| **Primary NAICS** | **337910** - Mattress Manufacturing |
| **Secondary NAICS** | **337127** - Institutional (Public Building) Furniture Manufacturing |
| **Federal PSC** | **7210** (Household Furnishings), **7105** (Household Furniture) |
| **Notification email** | **beford@silverlinesleep.com** |
| **EIN** | `[on file]` - keep out of version control; **differs from the old L.P.'s** |
| **Texas Taxpayer Number** | `[on file]` - keep out of version control; **differs from the old L.P.'s** |
| **Texas CMBL number** | `[on file]` |
| **Main phone** | `[on file]` |
| **Physical / remit address** | `[on file]` - Houston, TX (**no P.O. box** for SAM/EVS) |

---

## Name-suffix rules (the trap)

- The suffix is **`LLC`** (no periods). Write the legal name **exactly** as
  `CONTINENTAL SILVERLINE PRODUCTS, LLC` - including the comma before `LLC`.
- **Never** type `L.P.`, `Inc.`, `Corp.`, or drop `PRODUCTS`. Writing
  "Continental Silverline Products, L.P." is the **error** that this correction
  is undoing.
- On SAM/EVS, the legal name must match the **EIN letter / IRS records
  character-for-character** (including the suffix and punctuation). Match the LLC's
  documents, not memory.

## Where this must stay consistent

- SAM.gov entity record (needs a fresh LLC registration) - Texas CMBL - state
  portals (OK/LA/MS/AR/NM) - co-ops (TIPS, OMNIA, E&I, Sourcewell, etc.) - the
  capability statement (`vendor-profiles/`) - every registration runbook.
- **The Euna Supplier Network business profile already reads "Continental
  Silverline LLC" and is CORRECT - do NOT change it.** (A prior note wrongly told
  the operator to change it to L.P.; that instruction is cancelled.)
- **NM-SPD/Euna tenant** vendor record was submitted as "L.P." (2026-06-27) and
  must be edited to the LLC.

---

### Scope note
Docs only. Public identity values; PII (EIN, taxpayer number, etc.) kept out of
version control. Part of the 2026-06-27 L.P. -> LLC correction.
