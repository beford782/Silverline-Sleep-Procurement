# Entity Correction Plan - Continental Silverline Products, LLC (was wrongly recorded as L.P.)

- **For:** Blake / Continental Silverline Products, LLC
- **Date:** 2026-06-27
- **Source:** multi-agent scope (repo + online registrations + SAM/federal-impact research). The LLC is the ONLY real entity; L.P. was always a mistake (Blake-confirmed).

> **SUPERSEDED UPDATE (2026-06-28):** Use [`../entity_correction_briefing.md`](../entity_correction_briefing.md) and [`../entity_correction_checklist.md`](../entity_correction_checklist.md) as the current authority. Operator clarified the W-9/EIN is already LLC-correct, so this is not a repo-wide wrong-EIN/payment-mismatch problem. SAM.gov was verified as a wrong-named Work-In-Progress record under UEI `XF73FG8CVMX1`; do not complete banking or cite the UEI until self-service Entity Validation or FSD resolves correction vs. fresh validation/new UEI. NM-SPD/Euna was verified correct on 2026-06-28; no tenant L.P. edit is needed.

---

## The error in one line
The legal entity was recorded everywhere as "CONTINENTAL SILVERLINE PRODUCTS, L.P." (a limited partnership) when the authoritative Texas Comptroller/SOS record is **CONTINENTAL SILVERLINE PRODUCTS, LLC** (a Texas LLC, different EIN/taxpayer number)   " **Severity: HIGH / critical** (federal SAM registration and payment-capable state vendor records identify the wrong legal taxpayer).

## Corrected identity card
This is the authoritative replacement for `docs/company_identity.md`. Public values only.

| Field | Correct value |
|---|---|
| Legal name | **CONTINENTAL SILVERLINE PRODUCTS, LLC** |
| Entity type | **Texas Limited Liability Company (LLC)**   " not an L.P., not a corporation |
| State of formation | Texas |
| Formation / start year | **2015** (effective SOS registration 12/31/2015) |
| Texas SOS File Number | **0802357166** (public) |
| Registered Agent | **C T Corporation System**, 1999 Bryan St, Ste 900, Dallas, TX 75201 (public) |
| Status | Active |
| Formation document | Certificate of Formation (a Texas LLC files one) |
| EIN | [EIN on file]   " PII, never commit digits; differs from the L.P.'s |
| Texas Taxpayer Number | [taxpayer number on file]   " PII, never commit digits; differs from the L.P.'s |

Name-suffix rule (reversed from the old card): **always write "LLC"; never write "L.P.", "Inc.", or "Corp."** Drop the old false parenthetical "LPs do not have Articles of Incorporation/Organization." Do **not** instruct anyone to change the Euna profile's "Continental Silverline LLC" to L.P.   " that name is correct.

## Repo fixes
A PR I (the assistant) can produce. Grouped by file; cross-cutting rule: every "L.P." / "Limited Partnership"   ' "LLC" / "Limited Liability Company"; fill formation year 2015; add SOS File 0802357166 + Registered Agent where the identity is asserted.

**REVERSE this session's merged edits first (they actively spread the error):**
- [ ] `docs/company_identity.md`   " **reverse/rewrite to the Corrected identity card above.** Fix legal name (l.23), entity type (l.24), the L.P. framing (l.8-9), the false "LPs do not have Articles" parenthetical (l.25), the suffix rules (l.43-45   ' mandate LLC, forbid L.P./Inc./Corp.), and **delete the backwards instruction (l.47, l.57-59) telling the operator to change the correct Euna "Continental Silverline LLC" to L.P.** Add formation year 2015, SOS File 0802357166, Registered Agent, Status Active. Keep EIN/taxpayer as "[on file]".
- [ ] `docs/sam_uei_unblock_runbook.md`   " **reverse the L.P. assertions** at l.13, l.35, l.41, l.49, l.60; flip the suffix trap (l.74) so typing "L.P."/"Inc." is the error and "LLC" is correct; fix banking/remittance refs (l.102, 105, 110, 117-118). Add a prominent flag at l.16/32-33/106/134-137: **UEI XF73FG8CVMX1 may be bound to the wrong entity/EIN   " verify SAM legal name + EIN match the LLC; if under the L.P., treat as re-registration, not an edit.** Start year 2015, State TX, SOS File 0802357166. No EIN digits.

**Other docs (assert/instruct the wrong entity):**
- [ ] `docs/active_registrations.md`   " title + "For:" line (l.1, l.3)   ' LLC; SAM.gov row legal name (l.19)   ' LLC with a "verify SAM entity/EIN" note; **delete the backwards Euna follow-up at l.50 and l.85** and replace with a task to correct the NM-SPD Bonfire record (submitted as L.P.) to the LLC.
- [ ] `docs/nm_spd_euna_bonfire_registration_runbook.md`   " l.3 "For:", l.54, l.85-86   ' LLC / entity type LLC; add a correction note that the live NM-SPD Bonfire vendor record submitted as L.P. must be edited to the LLC.
- [ ] `docs/coop_ionwave_registration_runbook.md`   " l.3, l.20, l.44, l.50, l.72   ' LLC / entity type LLC (not yet submitted; fixing prevents seeding the error into HCDE/BuyBoard).
- [ ] `docs/research/system_audit_2026-06-27.md`   " l.3 "For:"   ' LLC; reframe the LLC-vs-L.P. guidance (l.14) so the trap is anyone writing "L.P."; l.35 and l.75 recommendations   ' "TX Limited Liability Company (LLC)", suffix example "LLC", start year 2015, SOS File 0802357166.
- [ ] `docs/awareness_system_design.md`   " l.3 header   ' LLC.

**Customer-facing / machine-readable:**
- [ ] `vendor-profiles/continental_silverline_capability_statement.md`   " l.1, l.18, l.44   ' Continental Silverline Products, LLC (a Texas LLC).
- [ ] `vendor-profiles/continental_silverline.profile.json`   " `legal_name`   ' "Continental Silverline Products, LLC"; keep dba/brands.
- [ ] `vendor-profiles/continental_silverline.md`   " l.9 Legal name   ' Continental Silverline Products, LLC.
- [ ] `vendor-profiles/continental_silverline_questionnaire.csv`   " l.6 company legal name   ' Continental Silverline Products, LLC.
- [ ] `generated/examples/continental_silverline.md` + `.html`   " regenerate from the corrected profile.

**CSV notes (corrective note acceptable; don't rewrite history):**
- [ ] `leads/review/_lead_radar.csv`   " rows 21, 44-46   ' LLC; **row 15: reverse the backwards Euna note** (Euna LLC is correct; note SAM/UEI entity must be verified to the LLC); note UEI XF73FG8CVMX1 is tied to the wrong L.P. entity/EIN and may need re-registration.
- [ ] `bids/archive/_pipeline_archive.csv`   " l.16 archive row   ' LLC (corrective note).

No EIN/taxpayer digits anywhere in the PR.

## Online corrections (operator)
Ordered by risk. **SAM.gov first.**

**TIER 1   " federal, do first / blocking**
1. **SAM.gov (UEI XF73FG8CVMX1)**   " STOP. **Do NOT complete the open Financial/EFT banking step** (sam_uei_unblock_runbook   6)   " finishing it cements the wrong entity. Open a Federal Service Desk ticket (fsd.gov, 866-606-8220). Because the LLC's EIN differs, plan for a **full new LLC registration / new UEI**, not an inline edit (see HIGH-RISK section).

**TIER 2   " payment-capable records storing a TIN (wrong EIN breaks 1099/payment matching: correct legal name AND resubmit LLC W-9/EIN)**
2. Oklahoma OMES Supplier Portal (Reg ID 0000018606)
3. Louisiana OSP / LaGov Supplier Self-Service (also fixes LSU/LaPAC enrollment downstream)
4. Mississippi DFA / MAGIC SUS (required before bidding FY26-27 dormitory furniture)
5. Arkansas OSP / ARBuy (Periscope/BSO)
6. Orleans Parish / New Orleans BRASS-Infor (Supplier 13390)
7. East Baton Rouge Parish VSS / Central Bidding (Vendor 1099)   " also reconcile the legacy duplicate vendor-email
8. Bexar County Infor (Supplier 17427)

**TIER 3   " co-op / county / university records (fix legal name to LLC; replace any L.P. W-9; re-point to LLC's NEW UEI where one is required)**
9. City of Houston (Beacon Bid)   " home city; resubmit LLC W-9
10. TIPS (Region 8), EPIC6 (Region 6), Region 4 ESC / OMNIA, E&I (JAGGAER), Sourcewell   " fix before any award
11. NM-SPD Euna/Bonfire tenant   " edit vendor record L.P.   ' LLC (newly created, alert-only; fix promptly)
12. El Paso County, Tarrant County (IonWave); Dallas County / BidNet Direct (one profile propagates across the six-state aggregation)
13. Texas A&M AggieBid, University of Oklahoma (OUHSC), Oklahoma State University (all JAGGAER)
14. Choice Partners / HCDE (IonWave)   " if unsubmitted, register fresh as LLC; if submitted, edit to LLC (UEI-gated)

**TIER 4   " verify only / not-yet-registered**
15. **Texas CMBL**   " verify it reads LLC + LLC taxpayer number; this is the canonical record to reconcile all others to.
16. Texas ESBD / SmartBuy   " verify no stray L.P. display name (inherits CMBL).
17. Walker County Bonfire   " confirm whether a vendor profile exists vs. RSS-only.
18. **BuyBoard (TASB)**   " not registered; register from the start as LLC (ignore the runbook's L.P. fields).
19. **Euna Supplier Network parent profile**   " already "Continental Silverline LLC". **DO NOT change to L.P.** (see below).

## HIGH-RISK / legal items
**The single most urgent action: STOP   " do not complete the SAM.gov Financial/EFT banking step, and stop citing UEI XF73FG8CVMX1 on any federal bid.** Completing banking cements a registration for the wrong legal taxpayer and creates real federal payment/1099 mismatch exposure.

In plain language (per the SAM finding, medium confidence, sourced to GSA/FSD/EXIM/FEMA guidance below):
- An **LLC and an L.P. are different legal persons** with different IRS EINs. SAM validates legal name + EIN character-for-character against IRS records, and the EVS assigns the UEI to one legal-name+address combination. So this is **not a cosmetic typo**   " the SAM record is a different entity than the one that should bid.
- **The EIN difference is the decisive blocker.** You generally cannot repurpose one entity's registration/UEI for a different entity. Expect a **full new SAM registration for the LLC** (validate via EVS against the LLC's Texas Certificate of Formation, SOS File 0802357166; register with the LLC's own EIN and matching IRS Taxpayer Name), which issues a **new UEI and new CAGE**.
- **UEI XF73FG8CVMX1 is permanent and non-transferable**   " it stays bound to the L.P. and cannot be renamed/converted to the LLC. Any award, CAGE, or rep/cert tied to it belongs to the L.P. Let the L.P. registration lapse/deactivate; do not renew it for LLC use. Re-point all downstream registrations to the LLC's NEW UEI once issued.
- **Honest caveat:** several of these are not "edits." The SAM re-registration, the IRS Taxpayer-Name/EIN reconciliation (CP-575 / 147C; Form 8822-B; IRS Business & Specialty line 1-800-829-4933), and the corrected W-9s on payment-capable state/county records may need an **accountant or attorney**, not just a portal change. Open the FSD ticket first to confirm the exact path for this fact pattern (wrong name + wrong entity type + different EIN).
- Sources: GSA EVS Stakeholder Forum FAQs (Sept 14 2022); sam.gov/alerts/entity-validation-0; FSD document standards (KB0055230); USDA ARS EVS "7 Common Mistakes"; EXIM.gov UEI/SAM; FEMA UEI guidance.
- **Never write EIN/taxpayer digits** into the repo or any output   " "[EIN on file]" / "[taxpayer number on file]" only.

## What was nearly broken
- **Euna Supplier Network parent profile was already CORRECT** ("Continental Silverline LLC"). The previously-logged follow-up (active_registrations.md task #4 and the company_identity.md note) instructed changing it **to** L.P.   " that instruction is itself the error. **Cancel it. Do NOT change the Euna profile to L.P.** Optionally refine the display to the exact "CONTINENTAL SILVERLINE PRODUCTS, LLC," but the entity is right.
- **NM-SPD Bonfire tenant was submitted WRONG this session** (as L.P.). It is newly created and alert-only (no EIN-critical payment yet), so an **inline edit** to the LLC fixes it   " do it promptly so it does not propagate, and so it matches the (correct) Euna profile and the LLC/SAM identity.
- **2026-06-28 superseding verification:** Euna Supplier Network / NM-SPD is correct; Business Profile reads "Continental Silverline LLC," no L.P. was found, and no tenant legal-name edit is needed.
