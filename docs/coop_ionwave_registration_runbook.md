# Co-op IonWave Registration Runbook — Choice Partners (HCDE) + BuyBoard

- **For:** Blake / Continental Silverline Products, L.P. (Houston, TX)
- **Date:** 2026-06-25
- **Type:** Operator runbook (docs only). Two vendor registrations to complete by hand.
- **Why now:** Both were UEI-gated. **SAM.gov UEI `XF73FG8CVMX1` is now assigned**, which unblocks the only field that was previously missing. Complete both while the UEI is fresh and the commodity setup matches the rest of the ledger.

> **Both portals run the same IonWave registration engine**, so the steps are identical: a 9-page wizard
> **Preliminary Info → Terms → Company Info → Addresses → Other Info → Commodity Codes → Classifications → Review → Complete**.
> Fill the same values on both so coverage stays consistent with [`active_registrations.md`](active_registrations.md).

> **PII rule:** values marked `[on file]` (CMBL/Vendor ID, EIN, phone, street address) are kept **out of version control** — pull them from your operator records / the CMBL profile when you fill the form. The **UEI is public** and is safe to type and to record here.

---

## What to have open before you start

| Item | Value / source |
|---|---|
| Legal name | **CONTINENTAL SILVERLINE PRODUCTS, L.P.** (a Limited Partnership — *not* LLC) |
| SAM.gov UEI | **XF73FG8CVMX1** |
| DUNS | Deprecated by the federal government (2022). Leave blank if optional; the UEI replaces it. |
| Main phone / Ext | `[on file]` |
| Physical address | `[on file]` — Houston, TX (no P.O. box) |
| Remit / mailing address | `[on file]` (same as physical unless you keep a separate remit) |
| Notification email | **beford@silverlinesleep.com** (forwards into the ingest funnel) |
| NAICS | 337910 (Mattress Mfg); 337127 (Institutional Furniture) |
| Capability statement | `vendor-profiles/continental_silverline_capability_statement.md` (fill placeholders on the sent copy) |
| W-9 | Have a signed PDF ready in case either portal requests an upload |
| Insurance summary | GL, auto, workers' comp, umbrella (certificate available on request) |

---

## Registration 1 — Choice Partners / HCDE

- **Registration URL:** `https://hcdeebid.ionwave.net/VendorRegistration.aspx` *(verified live 2026-06-25 — page heading "Preliminary Company Information")*
- **Public RFP board (reference):** https://www.choicepartners.org/current-rfps
- **Status going in:** Lead Radar `choice-partners-hcde-ffe-watch` — was *deferred → resume now*.
- **Why:** Local Houston co-op (Harris County Dept. of Education). Good for bed frames / FF&E. Next **Furniture, Fixtures, Equipment (FFE)** cycle estimated advertise **2027-06-01** — register now to be on the alert list for that re-bid.

### Step-by-step

1. **Preliminary Company Information** (page 1)
   - Company Name: `CONTINENTAL SILVERLINE PRODUCTS, L.P.`
   - Main Phone / Ext: `[on file]`
   - International: leave unchecked
   - **SAM.gov Unique Entity ID (UEI): `XF73FG8CVMX1`** ← the field that was blocking; now fillable
   - DUNS: leave blank (deprecated)
2. **Terms** — read and accept.
3. **Company Info** — legal name as above; entity type **Limited Partnership**; NAICS 337910 (+ 337127 if a second is allowed); website/catalog link if you have one.
4. **Addresses** — physical address `[on file]` (Houston, TX, **no P.O. box**); add remit/mailing if prompted.
5. **Other Info** — **set the notification/bid-alert email to `beford@silverlinesleep.com`.** Insurance carried: GL, auto, workers' comp, umbrella.
6. **Commodity Codes** — select the full set in the table below.
7. **Classifications** — Small Business: **Yes**; Resident (TX) Bidder: **Yes**; HUB/MBE/WBE/DBE: only if you actually hold the cert (a setup gap — leave unchecked if unsure).
8. **Review → Complete** — submit. Record the vendor/registration number it issues.

### Known checkpoint (do not skip)
The page accepts a **UEI-only** value; it does **not** validate against SAM "Active" status at registration time. If — and only if — the form blocks submission demanding an *active* SAM entity, stop and wait until SAM finishes (Financial/EFT banking is the last step). Otherwise proceed; this registration is positioning, not a live bid, so SAM-Active is not required to be on the alert list.

---

## Registration 2 — BuyBoard (TASB)

- **Registration URL:** `https://buyboard.ionwave.net/VendorRegistration` *(could not be auto-verified 2026-06-25 — IonWave returned HTTP 403 to the automated check, which is normal anti-scraping; confirm it loads in your browser. Same IonWave wizard as HCDE.)*
- **Co-op site (reference):** https://www.buyboard.com/
- **Status going in:** Lead Radar `buyboard-767-25` — `⬜ target`.
- **Why:** Largest TX local-gov co-op. Contract **#767 "Furniture for School, Office, Science, Library, and Dormitory"** explicitly names **dormitory furniture** — the single best dorm-furniture vehicle. #767-25 closed 2024-10-31; re-bid window est. **~2028** (verify). Register now so you're invited to the next furniture/dormitory RFP and to buys that never post publicly.

### Step-by-step
Identical IonWave wizard — use the **same values** as the HCDE steps above:
- Page 1: Company Name, Main Phone, **UEI `XF73FG8CVMX1`**, DUNS blank.
- Terms → Company Info (L.P. / NAICS 337910) → Addresses (`[on file]`, no P.O. box) → Other Info (**notification email `beford@silverlinesleep.com`**, insurance) → **Commodity Codes** (table below) → Classifications (Small Business Yes, TX Resident Yes) → Review → Complete.
- Record the vendor/registration number.

---

## Commodity codes — use the same selections on both portals

Select every NIGP code below that the portal's taxonomy offers; prioritize **205** and **420** if it caps the number.

| NIGP | Category |
|---|---|
| **205** | Bedding, Linens, Mattresses (parent) |
| 205-49 | Mattresses |
| 205-55 | Pillows *(we don't sell pillows — select only if it helps the bedding match; optional)* |
| **420** | Furniture: Dormitory / Household (parent) |
| 420-15 | Beds / Headboards |
| 420-20 | Dormitory Furniture, Wood (bed frames) |
| 420-26 | Dormitory Furniture |
| 420-68 | Mattresses & Bedsprings incl. fillers |

If the portal also takes free-text keywords, paste:

```
mattress, mattresses, bedding, box spring, bed frame, beds, bunk,
dormitory furniture, residence hall, Twin XL, institutional furniture,
FF&E, furniture and related services, correctional supplies, cots
```

> Product-fit note for routing expectations: these are broad **furniture co-op vehicles**, so most alerts land in **Lead Radar** (`co-op_contract_vehicle`). An explicit mattress/bed line inside a solicitation routes to the **Active pipeline** automatically via `relevance.py` — **do not** hand-promote a co-op vehicle to the active pipeline without a current open confirmed product-fit bid (the hard rule).

---

## After both are submitted

1. **Capture each vendor/registration number** in your private tracker (and tell me — I'll record the IDs).
2. **Update [`active_registrations.md`](active_registrations.md)** — flip the two co-op rows:
   - Choice Partners / HCDE: `🟡 deferred → resume now` → `✅ complete (2026-06-25)`, add the issued account ID.
   - BuyBoard: `⬜ target` → `✅ registered (2026-06-25)`, add the issued account ID.
3. **Update the two Lead Radar rows** (`choice-partners-hcde-ffe-watch`, `buyboard-767-25`) `last_reviewed` + notes to record "registration complete, UEI on file, notifications → funnel," keeping both as `watching` (no product-fit bid → they stay watches, not pipeline).
4. **Confirm the funnel sees a test alert** — once IonWave sends the first commodity notification to beford@silverlinesleep.com, verify it forwards and lands in Lead Radar (alerts are unwrapped by `tools/ingest_email.py`).

> I'll make the ledger + Lead Radar edits (one PR) as soon as you send back the two account IDs and confirm submission — that keeps the recorded state matching reality.

---

### Scope note
Docs only. No code, `configs/feeds.json`, CSV, or pipeline changes in this file. URLs are from the committed registry / operator checklist; HCDE verified live 2026-06-25, BuyBoard pending browser confirmation. PII (`[on file]`) stays out of version control; the UEI is public.
