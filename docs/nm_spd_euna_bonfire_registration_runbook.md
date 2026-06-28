# New Mexico SPD — Euna / Bonfire Registration Runbook

- **For:** Blake / Continental Silverline Products, LLC (Houston, TX)
- **Date:** 2026-06-26 (verified complete/correct 2026-06-28)
- **Type:** Operator runbook (docs only). One vendor registration to complete by hand.
- **Why now:** NM coverage is **partial**. The state's eProNM (SciQuest/JAGGAER) supplier
  registration is done, but New Mexico State Purchasing Division (SPD) is migrating its
  bid posting to the **Euna Supplier Network / NM-SPD Procurement Portal (Bonfire)**, and
  **SPD requires every supplier to register inside that NM-SPD portal — even suppliers who
  already hold a Euna/Bonfire account.** Completing this is what flips the NM row in
  [`active_registrations.md`](active_registrations.md) from `🟡 partial` to `✅ complete`.
- **Status:** verified complete/correct on 2026-06-28. The Euna Supplier Network Business
  Profile reads "Continental Silverline LLC," no "L.P." was found, and the profile propagates
  to the NM-SPD Bonfire tenant. Keep this runbook as historical setup/verification guidance.

> **Different engine from the co-op runbook.** Choice Partners / HCDE and BuyBoard run on
> **IonWave** ([`coop_ionwave_registration_runbook.md`](coop_ionwave_registration_runbook.md)).
> This one runs on **Euna/Bonfire**, so the flow is *create/confirm a Euna login → join the
> NM-SPD portal → fill the vendor profile → pick commodity categories → set the notification
> email*. Use the **same company values** as every other registration so coverage stays
> consistent with the ledger.

> **PII rule:** values marked `[on file]` (CMBL/Vendor ID, EIN, phone, street address) are
> kept **out of version control** — pull them from your operator records / the CMBL profile
> when you fill the form. The UEI is public, but if a future edit asks for SAM UEI, confirm
> the SAM correction status before adding or changing it.

---

## Portal facts (confirm the live cutover before relying on dates)

| Item | Value |
|---|---|
| **Register here** | **NM-SPD Procurement Portal (Euna/Bonfire):** `https://generalservices-state-nm-us.bonfirehub.com/` |
| Parent agency page | NM General Services Department, State Purchasing Division: `https://generalservices.state.nm.us/state-purchasing/` |
| Legacy portal (being retired) | eProNM (SciQuest/JAGGAER): `https://bids.sciquest.com/apps/Router/PublicEvent?CustomerOrg=StateOfNewMexico` — already registered (2026-06-21) |
| Lead Radar row | `new-mexico-spd-sciquest-portal` (status `watching`) |

> **Cutover dates (verified 2026-06-26 against the NM SPD "New eProcurement Platform"
> announcement on `generalservices.state.nm.us`):**
> - **eProNM (SciQuest/JAGGAER)** accepts supplier registration and bid responses **through
>   2026-06-22**.
> - **2026-06-29 go-live** — after this date **all new solicitations are posted exclusively
>   in the Euna/Bonfire NM-SPD Procurement Portal**, and you must be registered there to bid
>   on any new NM opportunity.
>
> **This is time-sensitive, not just positioning.** With go-live on **2026-06-29**, completing
> this registration is what keeps NM coverage live after eProNM stops carrying new bids — do it
> before the 29th. (A prior Lead Radar note said 2026-09-01; that was wrong and has been
> corrected to 2026-06-29.)

---

## What to have open before you start

| Item | Value / source |
|---|---|
| Legal name | **CONTINENTAL SILVERLINE PRODUCTS, LLC** (a Texas Limited Liability Company) |
| SAM.gov UEI | If a future edit asks for SAM UEI, confirm the SAM correction status before adding or changing it. |
| DUNS | Deprecated by the federal government (2022). Leave blank if optional; the UEI replaces it. |
| Main phone / Ext | `[on file]` |
| Physical address | `[on file]` — Houston, TX (**no P.O. box**) |
| Remit / mailing address | `[on file]` (same as physical unless you keep a separate remit) |
| **Notification email** | **beford@silverlinesleep.com** (forwards into the ingest funnel) |
| NAICS | 337910 (Mattress Mfg); 337127 (Institutional Furniture) |
| Capability statement | `vendor-profiles/continental_silverline_capability_statement.md` |
| W-9 | Have a signed PDF ready in case the portal requests an upload |
| Insurance summary | GL, auto, workers' comp, umbrella (certificate available on request) |

---

## Step-by-step

1. **Open the NM-SPD portal:** `https://generalservices-state-nm-us.bonfirehub.com/`.
   You should see a Bonfire-branded landing page for the State of New Mexico GSD/SPD with a
   **Login / Register** control (Bonfire is now part of the **Euna Supplier Network**).

2. **Create or sign in to your Euna/Bonfire login.**
   - If you have **no** Euna account: choose **Register / Create account**, enter
     **beford@silverlinesleep.com** as the account email, set a password, and **confirm via
     the verification email** that lands in the funnel mailbox.
   - If you already have a Euna login from another Bonfire tenant: sign in with it.
   - **Either way you must complete registration *inside the NM-SPD portal*** — SPD's rule is
     that a generic Euna account is not enough; the vendor record has to exist in this
     tenant. If the portal shows a "Register in this portal" / "Join" prompt after login,
     do it.

3. **Complete the vendor / company profile.**
   - Legal name: `CONTINENTAL SILVERLINE PRODUCTS, LLC`
   - Entity type: **Limited Liability Company**
   - SAM.gov UEI: if prompted in a future edit, confirm the SAM correction status before adding or changing it; DUNS: leave blank (deprecated).
   - Address: `[on file]` (Houston, TX, **no P.O. box**); add remit/mailing if prompted.
   - Main phone: `[on file]`.
   - Primary contact email / **bid-notification email: `beford@silverlinesleep.com`**.

4. **Select commodity codes / categories** (this is what drives the alerts — see the table
   below). Bonfire/Euna tenants use their own category tree (NIGP or UNSPSC depending on the
   tenant's setup), so **search the tree by keyword** and select every matching node:
   `mattress`, `bedding`, `beds`, `bed frame`, `cots`, `dormitory`, `residence hall`,
   `furniture`, `correctional`, `detention`, `shelter`, `hospital bed` / `patient bed`.

5. **Notification settings:** confirm category/bid notifications are **ON** and routed to
   **beford@silverlinesleep.com**. Set frequency to immediate/daily (not "off").

6. **Upload documents if requested:** W-9 and/or insurance/capability statement. None are
   required to be on the alert list, but attach what the form asks for.

7. **Submit / Finish.** Record the **vendor or supplier ID** the portal issues.

### Known checkpoint (do not skip)
This registration is **positioning** (getting on NM-SPD's alert list), not a live bid, so
**SAM "Active" is not required** to complete it — a UEI-only value is fine. If the form ever
hard-blocks on an *active* SAM entity, stop and wait until SAM finishes (Financial/EFT
banking is the last step — see [`sam_uei_unblock_runbook.md`](sam_uei_unblock_runbook.md) §6).

---

## Commodity codes / categories to select

Bonfire's tree may present **NIGP**, **UNSPSC**, or a custom list. Match by meaning; if NIGP
is offered, prioritize **205** and **420**.

| NIGP | Category |
|---|---|
| **205** | Bedding, Linens, Mattresses (parent) |
| 205-49 | Mattresses |
| **420** | Furniture: Dormitory / Household (parent) |
| 420-15 | Beds / Headboards |
| 420-20 | Dormitory Furniture, Wood (bed frames) |
| 420-26 | Dormitory Furniture |
| 420-68 | Mattresses & Bedsprings incl. fillers |

If the portal takes free-text keywords or lets you search the category tree, use:

```
mattress, mattresses, bedding, box spring, bed frame, beds, bunk,
cots, dormitory furniture, residence hall, institutional furniture,
correctional supplies, detention bedding, hospital bed, patient bed, FF&E
```

> **Routing expectation.** NM is a broad state-board channel, so most alerts land in **Lead
> Radar** (`other` / co-op style). A solicitation with an explicit mattress/bed line routes
> to the **Active pipeline** automatically via `relevance.py`. **Do not** hand-promote NM to
> the active pipeline without a current open, confirmed product-fit bid (the hard rule).

---

## After it is submitted

1. **Capture the vendor/supplier ID** in your private tracker (and tell me — I'll record it).
2. **Update [`active_registrations.md`](active_registrations.md)** — flip the NM row:
   `🟡 partial (2026-06-21)` → `✅ complete (2026-06-26)`, and add the issued account ID +
   note "Euna/Bonfire NM-SPD portal registration complete; eProNM + Euna both covered."
3. **Update Lead Radar row `new-mexico-spd-sciquest-portal`** (`last_reviewed` + notes) to
   record "NM-SPD Euna/Bonfire registration complete, UEI on file, notifications → funnel,"
   keeping it `watching` (no product-fit bid → it stays a watch, not pipeline).
4. **Confirm the funnel sees a test alert** — once the NM-SPD portal sends its first category
   notification to beford@silverlinesleep.com, verify it forwards and lands in Lead Radar
   (alerts are unwrapped by `tools/ingest_email.py`).

> I'll make the ledger + Lead Radar edits (one PR) as soon as you send back the vendor ID and
> confirm submission — that keeps the recorded state matching reality.

---

### Scope note
Docs only. No code, `configs/feeds.json`, CSV, or pipeline changes in this file. URLs are
from the committed `sources/procurement_sources.json` registry and the Lead Radar row; the
eProNM→Euna cutover dates (eProNM through 2026-06-22; Euna/NM-SPD exclusive 2026-06-29) were
verified 2026-06-26 against the NM SPD site. PII (`[on file]`) stays out of version control;
the UEI is public.
