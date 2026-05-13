# Bids

One markdown file per solicitation, named for the buyer's solicitation
or contract number.

```
bids/
  active/      In-progress: watching, drafting, or already submitted
  archive/     Closed: awarded, lost, no-bid
  templates/   Reusable response shells
```

## File naming

`<jurisdiction>-<solicitation-id>.md`, lowercased, dashes for spaces.
Examples:

- `bids/active/city-of-houston-q12345.md`
- `bids/archive/city-of-austin-ifb-8300-dcg1033.md`

## Status field

Each bid file should start with a short status block (see
`templates/bid_response_template.md`). The block is the source of
truth for fit, owner, and next action — easier to scan than digging
through the body text.

## Moving from active to archive

When a bid closes, move the file with `git mv` so the history follows
it:

```sh
git mv bids/active/<file>.md bids/archive/<file>.md
```

Update the status block to reflect the outcome (`awarded`, `lost`,
`no-bid`, `cancelled`) and the close date.

## What does NOT live here

- Raw downloaded solicitation PDFs — keep those in a private working
  tracker. The bid file references the URL or solicitation ID, not
  the document itself.
- Pricing worksheets and internal margin analysis — same reason.
- Vendor-side facts that apply across every bid — those go in
  `vendor-profiles/` once.
