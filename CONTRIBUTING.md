# Contributing

Thanks for working on the Silverline Sleep procurement toolkit. The repo
is intentionally small and document-first — keep additions in line with
the conventions below.

## Ground rules

- **Markdown + small Python utilities.** No web frameworks, no build
  steps. Python scripts should prefer the standard library; if a third
  party package is unavoidable, call it out in the script docstring.
- **Cross-platform paths.** Use forward slashes in docs and
  `os.path.join` / `pathlib` in scripts. Do not hard-code Windows
  drive letters or POSIX-only paths.
- **Domain terminology stays.** "Solicitation", "NIGP code",
  "commodity code", "bid", "IFB", "RFP", "IFQ" etc. are load-bearing —
  prefer them over softened consumer wording.
- **No personal contact data in version control.** Names, direct email,
  street addresses, phone numbers belong in a private working tracker,
  not in committed files. Use `private` as a placeholder in profiles.

## Where things go

| If you're adding... | Put it in |
| --- | --- |
| A new vendor's narrative profile | `vendor-profiles/<vendor>.md` |
| A new vendor's structured profile | `vendor-profiles/<vendor>.profile.json` (must pass the validator) |
| A filled-in questionnaire CSV | `vendor-profiles/<vendor>_questionnaire.csv` |
| A blank intake form | `templates/` |
| Portal/commodity-code plan | `portal-checklists/<vendor>_portal_setup.md` |
| Active solicitation tracking | `bids/active/<solicitation-id>.md` |
| Closed / awarded / no-bid | `bids/archive/<solicitation-id>.md` |
| Reusable bid response shell | `bids/templates/` |
| Python utility | `tools/` (legacy DreamFinder helpers go in `tools/legacy/`) |
| Tests | `tests/` (stdlib `unittest` — `python -m unittest discover -s tests`) |
| Committed example output | `generated/examples/` (regenerated with `--generated-date`) |
| Ad-hoc generated output | `build/` (gitignored, not committed) |

## Schema changes

When you change `vendor-profiles/vendor_profile.schema.json`:

1. Update every `vendor-profiles/*.profile.json` to match.
2. Run `python tools/validate_vendor_profile.py vendor-profiles/*.profile.json`
   and confirm they all pass.
3. Run `python -m unittest discover -s tests` and update tests if the
   schema's required/enum surface changed.
4. If you added a field, note it in the schema's `description` and in
   `vendor-profiles/README.md`.

## Style and hygiene

- Python: 4-space indent, snake_case, type hints encouraged. The repo
  is small enough that we don't yet require a formatter, but `ruff`
  and `black` defaults are fine.
- Markdown: 2-space indent for nested lists, ATX-style headings (`#`),
  one sentence per paragraph for diff-friendly editing.
- YAML/JSON: 2-space indent, UTF-8, LF line endings (enforced by
  `.editorconfig`).
- Filenames: kebab-case or snake_case, no spaces, lowercase.

## Pull requests

- Keep PRs focused. Restructuring is fine in one PR; mixing
  restructuring with new vendor content is not.
- For new vendor content, mention the vendor and the buyer audience in
  the PR description.
- Cite portal URLs only from `portal-checklists/<vendor>_portal_setup.md`
  references — don't sprinkle them through PR bodies.

## Git hygiene

A `pre-push` hook in `tools/hooks/` refuses non-fast-forward pushes to
`main`. To enable it locally:

```sh
git config core.hooksPath tools/hooks
```
