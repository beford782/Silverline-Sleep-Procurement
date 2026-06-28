# SAM.gov FSD Ticket — Entity Legal-Name Correction (L.P. → LLC)

- **For:** Blake / Continental Silverline Products, LLC
- **Date drafted:** 2026-06-28
- **Type:** Operator submission draft (docs only). Submit at **fsd.gov** (Create an Incident) or call **866-606-8220** (M–F 8am–8pm ET).
- **Why:** The SAM.gov Work-In-Progress entity registration was validated under the **wrong legal name** — it reads `CONTINENTAL SILVERLINE PRODUCTS, L.P.` There is no L.P.; the only real entity is the **LLC**. Verified in SAM.gov on 2026-06-28: status Work-In-Progress, UEI `XF73FG8CVMX1`, no CAGE, **no banking entered**.
- **PII rule:** Do **not** put the EIN/TIN or banking in this file or the ticket body. Provide those only in the form's own secure fields or if FSD specifically requests them. Placeholders below marked `[…]`.

> **Decision context:** Do **not** complete SAM Financial/EFT banking and do **not** cite UEI `XF73FG8CVMX1` on bids until this is resolved. SAM matches legal name + EIN against IRS; an "L.P." name against the LLC's EIN would likely fail the IRS match anyway. See [`entity_correction_checklist.md`](entity_correction_checklist.md) Tier 1.

---

## Ticket fields

**Category:** Entity Registration / Entity Validation
**Sub-category:** Legal Business Name correction

**Subject:**
Work-in-Progress entity registration validated under wrong legal name (L.P.) — must be the LLC

**Description:**

> My entity's Work-in-Progress registration in SAM.gov was created under an incorrect legal business name. It currently reads **"CONTINENTAL SILVERLINE PRODUCTS, L.P."** There is no L.P. entity — that name is an error. The only real, legally formed entity is **"CONTINENTAL SILVERLINE PRODUCTS, LLC,"** a Texas limited liability company.
>
> The registration has **not** been completed (no banking entered, status is Work in Progress, no CAGE assigned), so I want to correct this before finishing it rather than activate an entity under the wrong name.
>
> **Current (incorrect) record in SAM.gov:**
> - Legal Business Name: CONTINENTAL SILVERLINE PRODUCTS, L.P.
> - Unique Entity ID (UEI): XF73FG8CVMX1
> - Status: Work in Progress Registration
> - Physical Address: 710 N Drennan St, Houston, TX 77003-1321, USA
>
> **Correct entity (as it should read):**
> - Legal Business Name: **CONTINENTAL SILVERLINE PRODUCTS, LLC**
> - Entity type: Texas Limited Liability Company
> - State of formation: Texas
> - Date of formation / start year: 2015 (effective 12/31/2015)
> - Texas SOS file number: 0802357166
> - Registered agent: C T Corporation System, 1999 Bryan St Ste 900, Dallas, TX 75201
> - Physical Address: 710 N Drennan St, Houston, TX 77003-1321, USA
> - Taxpayer (TIN/EIN): on file — the LLC's own EIN (will provide securely if required)
>
> **My questions / request:**
> 1. Can the legal business name on this existing UEI (XF73FG8CVMX1) be corrected through Entity Validation to "CONTINENTAL SILVERLINE PRODUCTS, LLC," or does the corrected legal name require a new entity validation and a new UEI?
> 2. If a new validation/UEI is required, what is the correct procedure to retire or supersede the incorrect L.P. record so I don't end up with a duplicate entity?
> 3. The Taxpayer/TIN section was submitted for IRS match. I want to confirm the IRS validation runs against the **LLC's** legal name and EIN (not "L.P."), since a name/EIN mismatch would fail. Please advise the correct sequence.
>
> I can provide supporting documentation: Texas Secretary of State formation record for the LLC (file 0802357166), Texas Comptroller record showing the LLC as Active, and IRS EIN documentation (CP-575 / 147C) on request.

**Contact:**
- Name: Blake Ford
- Account email: beford@silverlinesleep.com
- Phone: [your callback number]
- Entity UEI: XF73FG8CVMX1

---

### Before you submit
- Have the **SOS formation record** (file 0802357166) and **EIN documentation** (CP-575 / 147C) ready to attach or reference.
- Question 1 is the crux: SAM usually binds the legal name to the UEI via Entity Validation, so the likely answer is "new validation → new UEI." Asking first avoids prematurely abandoning XF73FG8CVMX1 if FSD *can* correct it in place.
- **Alternative path (may be faster):** attempt self-service Entity Validation as the LLC (Register New Entity → validate "CONTINENTAL SILVERLINE PRODUCTS, LLC" at 710 N Drennan St). A Work-in-Progress registration isn't binding. If it assigns a clean new UEI, you've self-served it; if it conflicts/duplicates, file this ticket. Do **not** do both in parallel.
