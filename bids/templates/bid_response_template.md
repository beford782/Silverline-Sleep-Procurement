# {{Solicitation Title}}

| Field | Value |
| --- | --- |
| Status | watching / drafting / submitted / awarded / lost / no-bid |
| Buyer | {{Agency / Jurisdiction}} |
| Solicitation # | {{IFB / RFP / RFQ number}} |
| Portal | {{ESBD / Beacon Bid / Bonfire / IonWave / SAM.gov / cooperative}} |
| Posted | YYYY-MM-DD |
| Q&A deadline | YYYY-MM-DD |
| Response due | YYYY-MM-DD HH:MM CT |
| Award expected | YYYY-MM-DD |
| Vendor | {{vendor-profiles/<vendor>.md}} |
| Owner | {{name}} |
| Fit score | low / medium / high |
| Estimated value | ${{amount}} |

## 1. Scope summary

One paragraph describing what the buyer is asking for: product
categories, sizes, quantities, delivery scope, contract type
(fixed-quantity vs. term vs. as-needed), term length.

## 2. Commodity / NIGP codes

List the codes the solicitation is posted under. Cross-check against
`portal-checklists/<vendor>_portal_setup.md` to confirm we are
subscribed.

## 3. Fit assessment

- **Product fit:** which lines in `vendor-profiles/<vendor>.profile.json`
  `products` match the scope.
- **Compliance fit:** fire safety standards, vinyl/sealed covers,
  insurance limits, MOQs. Note any gaps.
- **Delivery fit:** does the buyer require inside delivery, removal,
  installation? Reconcile with `company.delivery_services`.
- **Pricing fit:** fixed price vs. escalation, term length vs. our
  price-hold tolerance.

## 4. Required documents

- [ ] Capability statement
- [ ] Product specification sheets
- [ ] Fire-safety / compliance certifications
- [ ] Warranty statement
- [ ] Insurance certificates (general liability, auto, workers comp,
      umbrella)
- [ ] W-9
- [ ] Conflict-of-interest / vendor forms
- [ ] Past-performance references
- [ ] HUB / MBE / WBE / DBE certifications (if applicable)

## 5. Open questions for the buyer

1. ...

## 6. Pricing approach

Notes on how we'll build pricing — line-item schedule, escalation
language, delivery handling, etc. Do not commit the pricing itself.

## 7. Decision

- **Bid / no-bid:** {{decision}}
- **Reason:** {{why}}
- **Next action:** {{owner — task — due date}}
