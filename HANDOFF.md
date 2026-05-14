# Claude Code handoff prompt

Copy the prompt below into a new Claude Code session when you want it
to catch up on this repository and continue work from the current
branch.

```text
You are working in the `Silverline-Sleep-Procurement` repository. Please first orient yourself to the current branch before making changes.

Context:
- This repo is a static procurement toolkit for institutional mattress bidding and vendor onboarding.
- It intentionally favors Markdown, CSV, JSON, HTML examples, and Python standard-library utilities over frameworks or external dependencies.
- The current work added a procurement toolkit with:
  - `tools/pipeline.py` for CSV opportunity pipeline management (`add`, `list`, `summary`, `score`, `move-to-archive`).
  - `tools/generate_procurement_packet.py` for Markdown and printable HTML packet generation from questionnaire CSVs.
  - `tools/validate_vendor_profile.py` for validating structured vendor profile JSON files.
  - `vendor-profiles/` data, schema, questionnaire examples, and generated reviewer-safe examples under `generated/examples/`.
  - workflow docs in `README.md`, `CONTRIBUTING.md`, `bids/README.md`, `procurement/README.md`, `onboarding/README.md`, `portal-checklists/`, `sources/`, `templates/`, and `tools/README.md`.
  - unit tests under `tests/test_pipeline.py` and `tests/test_procurement_tools.py`.

Start by running:

```bash
git status --short
git log --oneline -5
find .. -name AGENTS.md -print
sed -n '1,220p' README.md
sed -n '1,220p' tools/README.md
sed -n '1,220p' bids/README.md
sed -n '1,220p' procurement/README.md
```

Then inspect the key tools and tests:

```bash
sed -n '1,260p' tools/pipeline.py
sed -n '1,260p' tools/generate_procurement_packet.py
sed -n '1,220p' tools/validate_vendor_profile.py
sed -n '1,280p' tests/test_pipeline.py
sed -n '1,240p' tests/test_procurement_tools.py
```

Important repository conventions:
- Keep source materials diffable and cross-platform: prefer Markdown, CSV, JSON, and standard-library Python.
- Do not commit private portal credentials, tax IDs, private contact details, insurance certificates, sealed pricing, or unsigned legal documents.
- Keep private/generated working output in `build/generated/`; only commit `generated/examples/` files when sanitized and intentionally reviewer-safe.
- Maintain live bid work in `bids/active/` and closed work in `bids/archive/`.
- Reusable vendor facts belong in `vendor-profiles/` and structured JSON profiles should pass validation.
- Avoid adding dependencies unless clearly justified and documented.
- Preserve procurement terms like `solicitation`, `bid package`, `commodity code`, `portal registration`, `responsive`, and `responsible vendor`.

Useful validation commands:

```bash
python3 tools/generate_procurement_packet.py vendor-profiles/continental_silverline_questionnaire.csv --vendor "Continental Silverline" --output-dir build/generated --generated-date 2026-05-13
python3 tools/validate_vendor_profile.py vendor-profiles/continental_silverline.profile.json
python3 -m compileall tools
python3 -m unittest discover tests
git diff --check
```

If you are asked to make changes:
1. Read any applicable `AGENTS.md` files before editing. (None are committed at the moment; the `find` above will surface any that have been added.)
2. Inspect existing docs/tests before adding new patterns.
3. Keep the change focused and avoid rewriting generated examples unless necessary.
4. Run the relevant validation commands above.
5. Summarize changed files, tests run, and any limitations clearly.
```
