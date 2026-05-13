# Vendor Onboarding

Internal playbook for taking a new mattress vendor from "just
introduced" to "able to respond to a public-sector solicitation."

## End-to-end workflow

1. **Intake.** Send the vendor a copy of
   `templates/mattress_bid_setup_questionnaire.csv`. Ask them to fill
   in the **Your Answer** column. Anything sensitive can be marked
   `private`.
2. **Generate the packet.** When the CSV comes back, run:
   ```sh
   python tools/generate_procurement_packet.py path/to/answers.csv \
       --vendor "Vendor Name"
   ```
   That yields a markdown packet and a print-ready HTML version under
   `build/generated/` (gitignored). Pass `--output-dir
   generated/examples/ --generated-date YYYY-MM-DD` only when you
   intentionally want to update the committed example.
3. **Author the narrative profile.** Translate the packet into a
   sanitized public-sector pursuit profile at
   `vendor-profiles/<vendor>.md`. Strip contact details — use the
   structured profile for that data later if it ever needs to be
   committed, otherwise keep it out of the repo entirely.
4. **Author the structured profile.** Copy
   `vendor-profiles/continental_silverline.profile.json` as a starting
   shape. Validate:
   ```sh
   python tools/validate_vendor_profile.py vendor-profiles/<vendor>.profile.json
   ```
5. **Build the portal plan.** Copy
   `portal-checklists/continental_silverline_portal_setup.md` and
   adapt it. The "Commodity-Code Cleanup Strategy" section is reusable
   verbatim for any institutional mattress vendor.
6. **Stage opportunity tracking.** Create the first
   `bids/active/<solicitation-id>.md` once you have a real
   opportunity, even if it's only a watchlist entry.

## What "done" looks like

- [ ] `vendor-profiles/<vendor>_questionnaire.csv` committed
- [ ] `vendor-profiles/<vendor>.md` reviewed
- [ ] `vendor-profiles/<vendor>.profile.json` validated against the schema
- [ ] `portal-checklists/<vendor>_portal_setup.md` committed
- [ ] At least one entry under `bids/active/` or `bids/archive/`
- [ ] Generated packet linked from the vendor PR description

## Notes on sensitive data

The committed profile is a public-sector pursuit document, not a
relationship record. Direct contact info, pricing schedules, and
internal correspondence stay outside the repo. The structured JSON
profile is the right place to record things like service geography,
delivery method, and award history — durable facts that aid future
bid responses.
