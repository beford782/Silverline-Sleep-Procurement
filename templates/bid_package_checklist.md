# Bid Package Checklist

Reusable shell for assembling a public-sector mattress bid response.
Copy this file into your working tracker (or into the bid markdown
under `bids/active/<opportunity-id>.md`) and check items off as you
collect them. Not every item applies to every solicitation — strike
through the ones that don't and document buyer-specific additions in
section 8.

Pair this with the per-opportunity bid response markdown
(`bids/templates/bid_response_template.md`) and, if you've drafted
one, `build/drafts/<opportunity-id>_draft.md` from
`tools/draft_bid_response.py`.

## 1. Cover materials

- [ ] Cover letter on company letterhead, signed by an authorized
      officer
- [ ] Capability statement (1–2 pages)
- [ ] Table of contents (if the response exceeds 10 pages)
- [ ] Executive summary (if the buyer requests one)

## 2. Vendor information

- [ ] W-9 (current calendar year)
- [ ] Supplier registration form (buyer-specific, if required)
- [ ] Conflict-of-interest disclosure
- [ ] Non-collusion affidavit (if required)
- [ ] Debarment / suspension certification (if required)
- [ ] Federal funding certifications (if any federal pass-through)

## 3. Product / scope documentation

- [ ] Product specification sheets for each line item
- [ ] Fire-safety certifications (16 CFR Part 1632, 16 CFR Part 1633,
      CAL TB 117, NFPA-related as applicable)
- [ ] Institutional vinyl / sealed-cover documentation (if required)
- [ ] Tamper-resistant / correctional-grade construction notes
      (if required)
- [ ] Sample availability statement (sizes, timing, cost)
- [ ] Lead time and delivery schedule

## 4. Pricing

- [ ] Line-item pricing schedule (signed and dated)
- [ ] Pricing methodology and escalation language (foam / raw material
      protection if multi-year)
- [ ] Catalog discount documentation (if cooperative or catalog-based)
- [ ] Delivery cost breakdown (dock vs. inside vs. installation)
- [ ] Optional services pricing (removal, disposal, etc.)
- [ ] Bid-bond cost line (if a bid bond is required)

## 5. References and past performance

- [ ] Past-performance reference list (3+ recommended)
- [ ] Contracts of similar size and scope
- [ ] Contact name, title, phone, and email for each reference
- [ ] Reference-availability confirmations
- [ ] City of Austin IFB 8300 DCG1033 referenced (if applicable)

## 6. Insurance and legal

- [ ] Certificate of insurance: general liability
- [ ] Certificate of insurance: auto
- [ ] Certificate of insurance: workers' compensation
- [ ] Certificate of insurance: umbrella
- [ ] Bid bond (if required by solicitation)
- [ ] Performance bond statement (if a performance bond is required
      on award)
- [ ] Required signatures, notarization, and witness blocks

## 7. Compliance certifications (if applicable)

- [ ] Texas HUB certificate
- [ ] MBE / WBE / DBE certificate (federal / state / local)
- [ ] Small business certification
- [ ] Local business preference documentation
- [ ] ISO or other manufacturing certifications

## 8. Buyer-specific forms

List forms the buyer's solicitation specifically requires, per its
Required Forms / Appendix section:

- [ ] _Form name_ — _section reference_
- [ ] _Form name_ — _section reference_
- [ ] _Form name_ — _section reference_

## 9. Submission

- [ ] Format matches the buyer's instructions (PDF / portal upload /
      sealed envelopes / both)
- [ ] File naming matches the buyer's instructions
- [ ] Pre-submission peer review completed
- [ ] Final response submitted before the due date
- [ ] Submission confirmation receipt (portal screenshot, email,
      delivery receipt) saved
- [ ] Q&A deadline tracked and any addenda incorporated

## 10. Post-submission tracking

- [ ] Update `bids/active/<opportunity-id>.md` status to `submitted`
- [ ] Update `bids/active/_pipeline.csv` row via
      `python tools/pipeline.py add --opportunity-id ... --overwrite`
- [ ] Calendar entry for award-decision date
- [ ] Calendar entry for next follow-up

## What this checklist is NOT

- A substitute for reading the solicitation cover-to-cover. The buyer
  sets the rules; this list is a starting place.
- A pricing approach — see the bid response template's section 6.
- A no-bid memo — see `templates/no_bid_memo_template.md` if you
  decide not to bid.
