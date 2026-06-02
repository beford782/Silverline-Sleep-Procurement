# Bids

One markdown file per solicitation, named for the buyer's solicitation
or contract number.

```
bids/
  active/                In-progress: watching, drafting, or already submitted
    _pipeline.csv        Live opportunity pipeline (one row per opportunity)
  archive/               Closed: awarded, lost, no-bid, cancelled
    _pipeline_archive.csv  Archived rows moved out of active
  templates/             Reusable response shells
```

## Two layers

This folder holds two coordinated views of the same opportunities:

- **`_pipeline.csv`** — the structured pipeline, one row per
  opportunity. Sorted, scored, summarized, and moved via
  `tools/pipeline.py`. This is the source of truth for *what we are
  pursuing right now*.
- **`<jurisdiction>-<solicitation-id>.md`** — per-solicitation
  markdown using the bid-response template, holding the prose,
  open-questions list, and decision rationale that doesn't fit a CSV
  cell.

The CSV is for tracking; the markdown is for thinking. They share an
`opportunity_id` so the link is obvious.

## Starter drafts from the vendor profile

`tools/draft_bid_response.py` writes a starter response markdown to
`build/drafts/<opportunity-id>_draft.md` (gitignored) by combining a
pipeline row with a vendor profile JSON.

Promote the draft once it is worth committing:

```sh
python tools/promote_draft.py <opportunity-id>
```

The promoted file lands at `bids/active/<opportunity-id>.md`. The draft
is regenerable and is intentionally kept out of git.

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

## Working the pipeline

```sh
# Append a new opportunity row (default writes to bids/active/_pipeline.csv)
python tools/pipeline.py add \
    --source "Texas ESBD" \
    --buyer "Texas Facilities Commission" \
    --solicitation-number "IFB 529-XYZ" \
    --title "Dormitory mattresses pilot" \
    --due-date 2026-06-15

# See what's open, sorted by due_date (blanks last)
python tools/pipeline.py list

# Review active-work priorities
python tools/dashboard.py

# Counts by status, source, risk_level
python tools/pipeline.py summary

# Recompute fit_score and risk_level from text columns
python tools/pipeline.py score --dry-run
python tools/pipeline.py score   # apply

# Check for CSV/markdown/status drift
python tools/workflow_check.py

# Close out: move the CSV row to the archive
python tools/pipeline.py move-to-archive <opportunity-id>
```

When a bid closes, also move the matching markdown file with `git mv`
so history follows it:

```sh
git mv bids/active/<file>.md bids/archive/<file>.md
```

Update the status block in the markdown to match the new pipeline
row.

## What does NOT live here

- Raw downloaded solicitation PDFs — keep those in a private working
  tracker. The bid file references the URL or solicitation ID, not
  the document itself.
- Pricing worksheets and internal margin analysis — same reason.
- Vendor-side facts that apply across every bid — those go in
  `vendor-profiles/` once.
