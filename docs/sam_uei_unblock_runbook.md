# SAM.gov UEI Unblock Runbook — Continental Silverline

- **For:** Blake / Continental Silverline (Houston, TX)
- **Date:** 2026-06-24
- **Type:** Operator runbook (docs only). No code, no CSV writes, no PII stored here.
- **Goal:** Clear the SAM.gov **Entity Validation** failure so the **UEI is issued** and federal registration can complete. This is the single highest-leverage unblock — see [`wild_opportunity_discovery_strategy.md`](wild_opportunity_discovery_strategy.md) §"Federal direct lane".

> **Why this matters now.** The funnel is already catching genuine federal mattress fits (USCG Base Boston `37010PR260000078`; JBSA `FA301626Q0151`), but every one is a **forced no-bid** until an active UEI exists — you cannot submit a federal offer without it. Resolving validation converts captured demand into bid-eligible opportunities.

---

## 1. Diagnosis (confirmed 2026-06-24)

The UEI is free and instant; the wall is **Entity Validation (EVS)**. SAM's automated match failed, so it requires uploaded documents proving **four** data points, which must **exactly** match what you type into SAM:

| Data point | Status | Document that proves it |
|---|---|---|
| Legal business name | ✅ have | **IRS EIN letter** (CP-575 or 147C) |
| Physical address | ✅ have | **Bank or utility statement** (dated within 5 years; real street address) |
| **Start year** | ❌ **gap** | **TX Secretary of State formation record** (see §2) |
| **State of incorporation** | ❌ **gap** | Same TX SOS record (shows TX) |

Confirmed facts: "Continental Silverline" is a **formally registered TX entity under that exact legal name** (no brand-vs-legal-name mismatch), and SAM is **stuck at validation asking for documents**. So the only missing artifact is the **state formation record** — which is exactly the "incorporation / legal-start-year documentation" the blocker has always referred to.

---

## 2. The one missing document — get the TX SOS formation record

Because the entity is a formed TX LLC/corporation, its formation record is public. Two ways to obtain an acceptable document:

**Option A — Free official printout (fastest).**
- Texas Comptroller **Taxable Entity Search**: <https://mycpa.cpa.state.tx.us/coa/> — search the legal name; open the entity record.
- Or **Texas SOSDirect** business-organization inquiry: <https://www.sos.state.tx.us/corp/sosda/index.shtml>.
- **Print/screenshot the RESULTS page** showing the legal name, the **registration/formation date** (the start year), and **Texas** as the jurisdiction. SAM requires the capture to show the **search result AND the page URL** — not a blank form.

**Option B — Certified copy (most bulletproof).**
- Order a **Certificate of Formation** copy or **Certificate of Fact – Status** from SOSDirect (small fee, ~$15). A stamped/sealed Articles of Incorporation/Organization is the EVS "gold standard" and covers legal name + start year + state in one document.

> Use Option A first; fall back to Option B only if EVS rejects the printout.

---

## 3. Submit the validation (exact steps)

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
2. **Set the SAM.gov saved-search alert** for NAICS 337910 / PSC 7210 (Active) — see the Federal direct lane in [`wild_opportunity_discovery_strategy.md`](wild_opportunity_discovery_strategy.md).
3. **Resume the UEI-gated registrations**: Choice Partners / HCDE, and re-check any other source that required a UEI.
4. **Re-evaluate the live federal fits**: the recurring federal channels are tracked in `leads/review/_lead_radar.csv` (VA/VHA, Bureau of Prisons, Army/DoD barracks). The JBSA `FA301626Q0151` row (due **2026-07-01**) is almost certainly too soon for validation to clear — treat the UEI work as positioning for the **next** recurring federal mattress bid, not this one.

---

## 6. Sources

- SAM.gov Entity Validation: <https://sam.gov/entity-registration> · <https://sam.gov/alerts/entity-validation-0>
- SAM.gov Entity Registration Checklist (PDF): <https://sam.gov/sites/default/files/2024-11/entity-checklist.pdf>
- GSA / Federal Service Desk acceptable-documents guidance: <https://www.fsd.gov> · GSA "Tips for SAM.gov entity validation support": <https://interact.gsa.gov/blog/tips-samgov-entity-validation-support>

---

### Scope note
Operator runbook only. No code, CSV, or config changes. No EIN, address, or vendor IDs are stored in this file (PII stays out of version control, per the CMBL identity rule).
