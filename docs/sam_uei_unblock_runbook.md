# SAM.gov UEI Unblock Runbook — Continental Silverline

- **For:** Blake / Continental Silverline (Houston, TX)
- **Date:** 2026-06-24
- **Type:** Operator runbook (docs only). No code, no CSV writes, no PII stored here.
- **Goal:** Finish the full SAM.gov **Entity Registration** after the UEI was issued. This is the single highest-leverage federal unlock — see [`wild_opportunity_discovery_strategy.md`](wild_opportunity_discovery_strategy.md) §"Federal direct lane".

> **Why this matters now.** The funnel is already catching genuine federal mattress fits (USCG Base Boston `37010PR260000078`; JBSA `FA301626Q0151`). UEI assignment removed the first hard blocker, but federal offers still generally require the full SAM entity registration to be active.

## 0. Current SAM.gov status (updated 2026-06-25)

- **UEI assigned:** `XF73FG8CVMX1`
- **SAM entity display:** `CONTINENTAL SILVERLINE PRODUCTS, L.P.`
- **Entity registration type:** All Awards
- **Business / Business Types / Reps & Certs / Points of Contact:** Complete.
- **Taxpayer Information:** submitted to IRS verification; SAM shows "May Require Review; Avg. 2-5 Days."
- **Financial Information (EFT/banking):** **the last open section — this is the resume point.** Complete it per **§6** below.
- **CAGE code:** auto-requested by SAM/DLA during registration; may take a few business days to assign (a registration cannot go Active without it).
- **Saved-search notifications:** enabled for NAICS `337910` Active, PSC `7210` Active, and keyword `mattress` Active.
- **Do not treat as bid-ready yet:** wait until SAM shows the entity registration **Active**.

---

## 1. UEI unblock history (confirmed 2026-06-24)

The UEI was issued on 2026-06-24 after the entity validation/start-date blocker was cleared. Keep this section only as audit trail for future renewals or if SAM requests validation support again.

| Data point | Status | Document that proves it |
|---|---|---|
| Legal business name | ✅ have | **IRS EIN letter** (CP-575 or 147C) |
| Physical address | ✅ have | **Bank or utility statement** (dated within 5 years; real street address) |
| **Start year** | ❌ **gap** | **TX Secretary of State formation record** (see §2) |
| **State of incorporation** | ❌ **gap** | Same TX SOS record (shows TX) |

Confirmed result: SAM assigned UEI `XF73FG8CVMX1` for `CONTINENTAL SILVERLINE PRODUCTS, L.P.` at the Houston street address. The remaining work is the full registration checklist, especially IRS taxpayer verification and financial/payment information.

---

## 2. If SAM asks again: TX SOS formation record

Because the entity is a formed TX LLC/corporation, its formation record is public. Two ways to obtain an acceptable document:

**Option A — Free official printout (fastest).**
- Texas Comptroller **Taxable Entity Search**: <https://mycpa.cpa.state.tx.us/coa/> — search the legal name; open the entity record.
- Or **Texas SOSDirect** business-organization inquiry: <https://www.sos.state.tx.us/corp/sosda/index.shtml>.
- **Print/screenshot the RESULTS page** showing the legal name, the **registration/formation date** (the start year), and **Texas** as the jurisdiction. SAM requires the capture to show the **search result AND the page URL** — not a blank form.

**Option B — Certified copy (most bulletproof).**
- Order a **Certificate of Formation** copy or **Certificate of Fact – Status** from SOSDirect (small fee, ~$15). A stamped/sealed Articles of Incorporation/Organization is the EVS "gold standard" and covers legal name + start year + state in one document.

> Use Option A first; fall back to Option B only if EVS rejects the printout.

---

## 3. Historical validation steps

1. Sign in at <https://sam.gov> with the Login.gov account → **Entity Management / Get Started**.
2. In **Entity Validation**, if your entity isn't matched, choose **"I don't see my entity / my information is different"** to open an **incidental validation ticket**.
3. Enter the four data points so each **exactly** matches your documents:
   - **Legal business name** — match the EIN letter character-for-character, including (or excluding) the entity suffix ("LLC"/"Inc.") and punctuation.
   - **Physical address** — the street address on the bank/utility statement; **never a P.O. box**.
   - **Start year** — the formation/registration year on the TX SOS record.
   - **State of incorporation** — Texas.
4. **Upload** the documents (EIN letter + bank/utility statement + TX SOS record).
5. Submit. EVS review typically takes a few business days. Track or escalate via the **Federal Service Desk**: <https://www.fsd.gov> · **866-606-8220**.

---

## 4. Rejection traps to avoid (these cause repeat failures)

- **P.O. box** as the physical address → rejected every time. Use a street address.
- **Lease agreements** → rejected (private contracts, not public records).
- **Blank/original applications or a W-9** → rejected; only **processed/certified** documents count.
- **Any mismatch** between typed data and the documents (a different start year, an extra "LLC", an abbreviated street) → rejected. Make them identical.
- Document with **no certifying stamp/seal/URL** → rejected.

---

## 5. After the UEI is issued

1. **Complete the full entity registration** (required to *receive awards*, not just to hold a UEI):
   - Add **NAICS `337910`** (Mattress Mfg) and `337127` (Institutional Furniture); **PSC `7210`** / `7105`.
   - Complete **Reps & Certs**, points of contact, and **banking/EFT (CAGE)** info.
2. **Maintain and monitor SAM.gov saved-search alerts** for NAICS 337910 / PSC 7210 / keyword mattress (Active) — see the Federal direct lane in [`wild_opportunity_discovery_strategy.md`](wild_opportunity_discovery_strategy.md).
3. **Resume the UEI-gated registrations**: Choice Partners / HCDE, and re-check any other source that required a UEI.
4. **Re-evaluate the live federal fits**: the recurring federal channels are tracked in `leads/review/_lead_radar.csv` (VA/VHA, Bureau of Prisons, Army/DoD barracks). The JBSA `FA301626Q0151` row (due **2026-07-01**) is almost certainly too soon for validation to clear — treat the UEI work as positioning for the **next** recurring federal mattress bid, not this one.

---

## 6. Finish the Financial / EFT section (the last step) → Active

This is the **resume point** as of 2026-06-25. Everything else is Complete; the
Financial Information section is what's left, after which the registration is
submitted and works toward **Active**. Banking entry is **operator-only** — the
values below are not stored in this repo (PII rule); have them in hand before
you start.

### 7a. Have these ready (from operator records — do NOT commit)
| Item | Notes |
|---|---|
| **ABA routing number** | 9-digit routing for the business bank account |
| **Account number** | Business **checking** (or savings) account in the **legal entity name** (`CONTINENTAL SILVERLINE PRODUCTS, L.P.`) |
| **Account type** | Checking or Savings |
| **ACH / EFT bank contact** | The bank's ACH dept U.S. phone + email (SAM's EFT block asks for an ACH point of contact) |
| **Remittance name + address** | Where paper remittance would go if EFT fails — the L.P.'s name + Houston street address (no P.O. box) |
| **EIN + exact legal name** | Must match the IRS letter for the TIN match already in progress |

### 7b. Steps
1. Sign in at <https://sam.gov> → **Workspace → Entity Management** → open the
   `CONTINENTAL SILVERLINE PRODUCTS, L.P.` registration → **Financial Information**.
2. **Electronic Funds Transfer (EFT):** enter **ABA routing number**, **account
   number**, and **account type**. Double-check digits — a transposed routing/
   account number means federal payments fail.
3. **ACH / Automated Clearing House contact:** enter the bank's ACH dept U.S.
   phone and email (or the company's accounts-receivable contact if SAM accepts
   that). Fax is optional.
4. **Remittance address:** enter the L.P.'s remittance name + street address.
5. **Accounts Receivable POC** (if prompted in this section): the L.P.'s AR
   contact — name, address, phone, email.
6. **Review → Submit** the entire registration.

### 7c. What happens after submit (and what "done" looks like)
1. Registration moves to **Submitted / Processing**.
2. **IRS TIN match** must clear (the 2–5 day item already pending) — legal name
   + EIN must match IRS records exactly, or it bounces back as "needs review."
3. **CAGE code** is assigned by DLA (a few business days). The registration
   **cannot go Active without it** — this is the most common "why is it still
   not Active?" cause; it's normal, just wait.
4. When all three clear, SAM status flips to **Active** with an expiration date
   (~12 months; SAM requires **annual renewal**). **Only then is the entity
   award-eligible** — i.e., a federal offer can actually be submitted.

### 7d. Common Financial-section delay/rejection traps
- **TIN/name mismatch** with the IRS — the #1 Active blocker. The name on SAM
  must match the EIN letter character-for-character.
- **Bank account not in the legal entity's name** — use the L.P.'s account, not
  a personal or DBA-only account.
- **Routing/account typo** — silently breaks payment, not registration; verify
  against a voided check or bank letter.
- **Expecting instant Active after submit** — CAGE + TIN match add days. Don't
  read "Submitted" as a failure.

### 7e. The moment it goes Active — do these
- Flip the **SAM.gov row in [`active_registrations.md`](active_registrations.md)**
  from `🟡 UEI assigned, registration in progress` to `✅ active`, and record the
  **CAGE code** + registration expiration date (tell me; I'll do the doc PR).
- **Re-evaluate live federal fits** in `leads/review/_lead_radar.csv` (VA/VHA,
  Bureau of Prisons, Army/DoD barracks) — these become submittable.
- Note: **JBSA `FA301626Q0151`** (due **2026-07-01**) is almost certainly too
  soon — the UEI/registration work positions for the **next** recurring federal
  mattress bid, not this one. (The overseas `FA568226QA053` was already a
  structural no-bid, archived 2026-06-25.)

---

## 7. Sources

- SAM.gov Entity Validation: <https://sam.gov/entity-registration> · <https://sam.gov/alerts/entity-validation-0>
- SAM.gov Entity Registration Checklist (PDF): <https://sam.gov/sites/default/files/2024-11/entity-checklist.pdf>
- GSA / Federal Service Desk acceptable-documents guidance: <https://www.fsd.gov> · GSA "Tips for SAM.gov entity validation support": <https://interact.gsa.gov/blog/tips-samgov-entity-validation-support>

---

### Scope note
Operator runbook only. No code, CSV, or config changes. No EIN, address, or vendor IDs are stored in this file (PII stays out of version control, per the CMBL identity rule).
