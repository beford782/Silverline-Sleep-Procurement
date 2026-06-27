# Company Identity — Canonical Card

- **Purpose:** One authoritative place for the company's legal identity so every
  registration, bid, runbook, and capability statement uses the **same values**.
  When a portal or form asks "what's the legal name / entity type / UEI / NAICS,"
  copy from here. If any other doc disagrees with this card, **this card wins** —
  fix the other doc.
- **Why this exists:** The recurring failure mode is the **LLC-vs-L.P. mix-up**
  (the entity is a *Limited Partnership*, not an LLC). A name/entity-type mismatch
  against the SAM.gov/UEI record can hold up a contract award. See
  [`active_registrations.md`](active_registrations.md).

> **PII rule:** values marked `[on file]` — **EIN, CMBL number, phone, street
> address** — are kept **out of version control** (operator records only). The
> **UEI, legal name, entity type, NAICS, and PSC are public** and safe to record.

---

## The card

| Field | Value |
|---|---|
| **Legal name** | **CONTINENTAL SILVERLINE PRODUCTS, L.P.** |
| **Entity type** | **Texas Limited Partnership (L.P.)** — *not* an LLC, *not* a corporation |
| **Formation doc** | **Certificate of Formation** (Texas SOS). LPs do **not** have "Articles of Incorporation/Organization." |
| **State of formation** | Texas |
| **SAM.gov UEI** | **XF73FG8CVMX1** (public) |
| **DUNS** | Deprecated by the federal government (2022) — leave blank; the UEI replaces it. |
| **Primary NAICS** | **337910** — Mattress Manufacturing |
| **Secondary NAICS** | **337127** — Institutional (Public Building) Furniture Manufacturing |
| **Federal PSC** | **7210** (Household Furnishings), **7105** (Household Furniture) |
| **Notification email** | **beford@silverlinesleep.com** (forwards into the ingest funnel) |
| **EIN** | `[on file]` (keep out of version control) |
| **Texas CMBL number** | `[on file]` |
| **Main phone** | `[on file]` |
| **Physical / remit address** | `[on file]` — Houston, TX (**no P.O. box** for SAM/EVS) |
| **Formation / start year** | `[on file]` — must match the TX SOS record + EIN letter exactly. |

---

## Name-suffix rules (the trap)

- The suffix is **`L.P.`** (with periods). Write the legal name **exactly** as
  `CONTINENTAL SILVERLINE PRODUCTS, L.P.` — including the comma before `L.P.`
- **Never** type `LLC`, `Inc.`, `Corp.`, or drop `PRODUCTS`. A casual shorthand
  like "Continental Silverline LLC" is **wrong** and has appeared in real
  registrations (e.g. the Euna Supplier Network business profile) — correct it
  wherever it shows up.
- On SAM/EVS, the legal name must match the **EIN letter character-for-character**
  (including the suffix and punctuation). Match the documents, not your memory.

## Where this must stay consistent

- SAM.gov entity record · Texas CMBL · state portals (OK/LA/MS/AR/NM) · co-ops
  (TIPS, OMNIA, E&I, Sourcewell, etc.) · the capability statement
  (`vendor-profiles/`) · every registration runbook.
- Known open correction: the **Euna Supplier Network business profile** legal
  name still reads "Continental Silverline LLC" → change to
  `CONTINENTAL SILVERLINE PRODUCTS, L.P.` (tracked in
  [`active_registrations.md`](active_registrations.md)).

---

### Scope note
Docs only. Public identity values; PII kept out of version control per the rule
above. NAICS/PSC/UEI mirror `docs/active_registrations.md` and
`docs/sam_uei_unblock_runbook.md`.
