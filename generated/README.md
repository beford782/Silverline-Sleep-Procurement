# Generated Output

Output of scripts in `tools/`. Files here are not hand-edited; if you
need to change them, change the input and re-run the generator.

Committing generated output is a deliberate choice: it makes the repo
useful as-is without forcing every reader to run Python, and it lets
PRs review the rendered packet alongside the input that produced it.

## Current samples

| File | Generated from |
| --- | --- |
| `continental_silverline.md` | `vendor-profiles/continental_silverline_questionnaire.csv` |
| `continental_silverline.html` | same |

## Regenerate

```sh
python tools/generate_procurement_packet.py \
    vendor-profiles/continental_silverline_questionnaire.csv \
    --vendor "Continental Silverline" --out-dir generated/
```
