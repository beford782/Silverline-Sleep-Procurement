# Generated output

Two roles for this folder:

| Path | Role | Tracked? |
| --- | --- | --- |
| `generated/examples/` | Committed reference output for reviewers. Regenerated deterministically with `--generated-date`. | yes |
| (none — defaults route elsewhere) | Default output of new runs writes to `build/generated/`. | no (gitignored) |

The split prevents a routine `python tools/generate_procurement_packet.py …`
from overwriting the committed example. If you intentionally want to
update the example, pass `--output-dir generated/examples/` and pin
`--generated-date` so the diff is reviewable.

## Regenerating the committed example

```sh
python tools/generate_procurement_packet.py \
    vendor-profiles/continental_silverline_questionnaire.csv \
    --vendor "Continental Silverline" \
    --output-dir generated/examples/ \
    --generated-date 2026-05-13
```

## Currently committed samples

| File | Generated from |
| --- | --- |
| `examples/continental_silverline.md` | `vendor-profiles/continental_silverline_questionnaire.csv` |
| `examples/continental_silverline.html` | same |
