# SAM.gov Registration Runbook — Continental Silverline Products, LLC

- **For:** Blake / Continental Silverline Products, LLC (Houston, TX)
- **Date:** 2026-06-24 (entity correction added 2026-06-27)

> # 🛑 STOP — WRONG ENTITY. READ FIRST.
> The existing SAM registration and UEI **`XF73FG8CVMX1` were created for "CONTINENTAL
> SILVERLINE PRODUCTS, L.P." — an entity that DOES NOT EXIST.** The only real entity is
> **CONTINENTAL SILVERLINE PRODUCTS, LLC** (a Texas LLC, SOS file 0802357166, with its own
> EIN). See [`company_identity.md`](company_identity.md) and
> [`research/entity_correction_plan_2026-06-27.md`](research/entity_correction_plan_2026-06-27.md).
>
> - **DO NOT complete the Financial/EFT banking step (§6)** on the L.P. registration — it cements
>   the wrong taxpayer and creates federal payment/1099 exposure.
> - **DO NOT cite UEI `XF73FG8CVMX1` on any federal bid.** It is permanent and bound to the L.P.;
>   it cannot be renamed to the LLC.
> - **First action:** open a **Federal Service Desk** ticket (<https://www.fsd.gov> · 866-606-8220)
>   to confirm the path for *wrong legal name + wrong entity type + different EIN*. Expect a
>   **full new SAM registration for the LLC** (validated against the LLC's Certificate of Formation,
>   SOS file 0802357166, and its own EIN) issuing a **NEW UEI + new CAGE**. Let the L.P. registration
>   lapse.
> - This may need an **accountant/attorney** (IRS taxpayer-name/EIN reconciliation, corrected W-9s),
>   not just a form change.
>
> **The mechanical steps below are reusable for the LLC's fresh registration** — but use the LLC's
> legal name, EIN, and start year 2015 everywhere, and ignore any reference to the old L.P. UEI.

- **Goal (corrected):** Register **Continental Silverline Products, LLC** in SAM.gov from scratch under
  its own EIN, so the LLC (not the defunct L.P.) becomes award-eligible.

## 0. Status (corrected 2026-06-27)

- **L.P. registration:** WRONG ENTITY — do not finish or fund it. UEI `XF73FG8CVMX1` is the L.P.'s; abandon it.
- **LLC registration:** NOT STARTED — needs a fresh SAM entity registration under the LLC's EIN (validate
  via EVS against the LLC's TX Certificate of Formation / SOS file 0802357166, start year 2015).
- **Saved-search notifications** (NAICS `337910`, PSC `7210`, keyword `mattress`) can stay configured.
- **Do not treat as bid-ready:** no federal bids until the **LLC** registration shows Active with a new UEI.

---

## 1. UEI unblock history (confirmed 2026-06-24)

The UEI was issued on 2026-06-24 after the entity validation/start-date blocker was cleared. Keep this section only as audit trail for future renewals or if SAM requests validation support again.

| Data point | Status | Document that proves it |
|---|---|---|
| Legal business name | ✅ have | **IRS EIN letter** (CP-575 or 147C) |
| Physical address | ✅ have | **Bank or utility statement** (dated within 5 years; real street address) |
| **Start year** | ❌ **gap** | **TX Secretary of State formation record** (see §2) |
| **State of incorporation** | ❌ **gap** | Same TX SOS record (shows TX) |

Confirmed result: SAM assigned UEI `XF73FG8CVMX1` for `CONTINENTAL SILVERLINE PRODUCTS, LLC` at the Houston street address. The remaining work is the full registration checklist, especially IRS taxpayer verification and financial/payment information.

---

## 2. If SAM asks again: TX SOS formation record

Because the entity is a formed **TX limited liability company (LLC)**, its formation record is public. (Legal name/entity type per [`company_identity.md`](company_identity.md): **CONTINENTAL SILVERLINE PRODUCTS, LLC**.) Two ways to obtain an acceptable document:

**Option A — Free official printout (fastest).**
- Texas Comptroller **Taxable Entity Search**: <https://mycpa.cpa.state.tx.us/coa/> — search the legal name; open the entity record.
- Or **Texas SOSDirect** business-organization inquiry: <https://www.sos.state.tx.us/corp/sosda/index.shtml>.
- **Print/screenshot the RESULTS page** showing the legal name, the **registration/formation date** (the start year), and **Texas** as the jurisdiction. SAM requires the capture to show the **search result AND the page URL** — not a blank form.

**Option B — Certified copy (most bulletproof).**
- Order a **Certificate of Formation** copy or **Certificate of Fact – Status** from SOSDirect (small fee, ~$15). A stamped/sealed **Certificate of Formation** is the EVS "gold standard" and covers legal name + start year + state in one document. (An LLC files a Certificate of Formation — it does **not** have "Articles of Incorporation/Organization.")

> Use Option A first; fall back to Option B only if EVS rejects the printout.

---

## 3. Historical validation steps

1. Sign in at <https://sam.gov> with the Login.gov account → **Entity Management / Get Started**.
2. In **Entity Validation**, if your entity isn't matched, choose **"I don't see my entity / my information is different"** to open an **incidental validation ticket**.
3. Enter the four data points so each **exactly** matches your documents:
   - **Legal business name** — match the EIN letter character-for-character, including the entity suffix (here **`LLC`** — *not* "L.P."/"Inc.") and punctuation.
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
- **Any mismatch** between typed data and the documents (a different start year, the wrong suffix — e.g. typing "L.P." when the entity is an **"LLC"** — an abbreviated street) → rejected. Make them identical.
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
| **Account number** | Business **checking** (or savings) account in the **legal entity name** (`CONTINENTAL SILVERLINE PRODUCTS, LLC`) |
| **Account type** | Checking or Savings |
| **ACH / EFT bank contact** | The bank's ACH dept U.S. phone + email (SAM's EFT block asks for an ACH point of contact) |
| **Remittance name + address** | Where paper remittance would go if EFT fails — the LLC's name + Houston street address (no P.O. box) |
| **EIN + exact legal name** | Must match the IRS letter for the TIN match already in progress |

### 7b. Steps
1. Sign in at <https://sam.gov> → **Workspace → Entity Management** → open the
   `CONTINENTAL SILVERLINE PRODUCTS, LLC` registration → **Financial Information**.
2. **Electronic Funds Transfer (EFT):** enter **ABA routing number**, **account
   number**, and **account type**. Double-check digits — a transposed routing/
   account number means federal payments fail.
3. **ACH / Automated Clearing House contact:** enter the bank's ACH dept U.S.
   phone and email (or the company's accounts-receivable contact if SAM accepts
   that). Fax is optional.
4. **Remittance address:** enter the LLC's remittance name + street address.
5. **Accounts Receivable POC** (if prompted in this section): the LLC's AR
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
- **Bank account not in the legal entity's name** — use the LLC's account, not
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
