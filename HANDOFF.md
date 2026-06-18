# Resume prompt — Silverline-Sleep-Procurement

Copy the block below into a new Claude Code session to pick up work. Keep it
current as the project evolves (it replaced an older, stale handoff).

```text
You are resuming work on the Silverline-Sleep-Procurement repository — a static,
stdlib-Python procurement toolkit that surfaces contract MATTRESS opportunities
(federal/state/local/private) into one human-reviewed pipeline. Vendor: Continental
Silverline (Houston TX; brands Restonic/Spring Air/Silverline Sleep; institutional/
dormitory/correctional/medical/fire-retardant mattresses; service geography
TX/OK/LA/MS/AR/NM). Final bid submission is always manual/human.

Work branch: claude/serene-darwin-v8xfbq. Trunk: main.
GitHub: beford782/silverline-sleep-procurement (use mcp__github__* tools; no gh CLI).

## Hard constraints
- Standard-library Python only (third-party needs approval).
- No portal scraping / no browser automation. Public/documented APIs, RSS, or email only.
- No automatic bid submission. No committed secrets/credentials/private contacts/machine paths.
- Markdown/CSV/JSON/HTML over binary. Preserve procurement terminology.
- Branch + PR for non-trivial work; DO NOT open a PR unless asked.
- Audit gate before every commit:
    python -m unittest discover -s tests
    python -m compileall -q tools tests
    python -m json.tool on every committed JSON
    python tools/validate_vendor_profile.py vendor-profiles/continental_silverline.profile.json
    python tools/workflow_check.py
    machine-path / personal-name leak grep over committed py/md/json/csv
      (exact regex lives in .github/workflows/ci.yml — do not paste it into a
      committed .md file or it self-matches the grep)

## Architecture (the core idea)
Every channel feeds raw items into ONE central mattress-relevance filter
(tools/relevance.py) that gates the pipeline: ACCEPT (write), REVIEW (write +
"HUMAN: confirm scope" flag), REJECT (drop). Channels are pluggable adapters.

## Merged to main (PRs #19, #20)
- tools/relevance.py — classifier: whole-word/phrase matching; NAICS 337910 / PSC 7210 =
  strong; six-state geography demotion; require_procurement guard + noise-host filter for
  web sources. Tests: tests/test_relevance.py.
- tools/ingest_sam.py — SAM.gov federal API, relevance-gated. Workflow weekly_sam_ingest.yml
  (needs SAM_API_KEY secret).
- tools/ingest_email.py — portal commodity-alert emails; backends --provider graph (Outlook/
  M365, GRAPH_* secrets) and gmail (GMAIL_*); --check, --fixture. Workflow weekly_email_ingest.yml.
  Setup: docs/email_ingest_setup.md.
- tools/ingest_rss.py — RSS/Atom (Bonfire /opportunities/rss, Google Alerts w/ redirect-unwrap),
  relevance-gated. configs/feeds.json (public Bonfire feeds: Harris County, UT Austin, UT Health
  San Antonio). Workflow weekly_rss_ingest.yml (no secrets). Smoke-tested live 2026-06-17:
  53 open bids -> 0 mattress -> no PR (correct).
- validate_vendor_profile.py --schema works in any arg position.
- Tinker AFB Sources Sought triaged to no-bid (specified Purple brand; Continental doesn't make it).

## On branch claude/serene-darwin-v8xfbq, NOT yet merged
- .github/workflows/cleanup_auto_branches.yml — auto-deletes disposable auto/* ingest branches
  when their PR closes.
- Removed tools/legacy/ (non-procurement DreamFinder leftovers) + its test; refreshed this HANDOFF.

## Pipeline state
0 active rows. Federal (SAM) + state/local-web (RSS/Bonfire) funnels are LIVE, run Mondays, and
stay silent unless a real mattress bid appears (then a triage PR). ~243 tests pass.

## Open decisions / next steps (priority order)
1. EMAIL ROUTING (highest mattress hit-rate; unresolved). Alerts live in Outlook
   (beford@silverlinesleep.com); Azure/Graph admin consent off the table (owner has no privileged
   tenant role). Options: (a) forward Outlook->Gmail then ingest via --provider gmail or on-demand
   "pull my alerts" sweeps through the connected Gmail (works now, no OAuth); (b) change the
   notification email to blake.e.ford@gmail.com on the top ~5 portals.
2. Add more Bonfire/portal feeds to configs/feeds.json for breadth (need the operator's registered
   subdomains, e.g. University of Houston, City of Houston).
3. Open the cleanup PR for the branch items above when asked.
4. Optional later adapters (all gated by relevance.py): USASpending awards API (free, no key —
   lead-gen: who already buys mattresses, best path into private); Oklahoma data.ok.gov CKAN
   "Statewide Contracts & Solicitations" dataset (only in-region state with a real machine feed);
   Socrata Discovery (big-city open-bid datasets); paid GovSpend API ($8.5k+/yr, SLED, no private);
   IonWave per-sender email parser (lower priority now the central filter exists).

## Research already done (don't redo)
No nationwide API for state/local/private open solicitations. SAM=federal API; USASpending=federal
awards (free). State/local mostly email-only (OK CKAN is the lone in-region machine feed; TX ESBD/
LA/MS/AR/NM none). Aggregators: only GovSpend self-serve API (paid, no private); DemandStar/BidNet/
BidPrime/Periscope/Euna = email-only. Bonfire = only e-proc platform with public per-portal RSS.
Private sector has no central feed (GPO/approved-supplier rosters like Avendra/BirchStreet are how
it's won). Codes: NAICS 337910 (mattress mfg), PSC 7210 (household furnishings=mattresses/bedding),
PSC 7105 (furniture/beds).

Start by: git log --oneline -8; git status; python tools/dashboard.py; python -m unittest discover -s tests.
Then confirm the email-routing decision (#1) with the operator before building further.
```
