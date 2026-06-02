# Legacy tools

These scripts predate the procurement split — they were built for the
DreamFinder consumer application and ship here only because deleting
them would orphan any external workflow still pointing at this
checkout.

They are **not part of the procurement toolkit**:

- `convert_store_data.py` reads a DreamFinder retailer onboarding
  `.xlsx` and emits CSS / JS / accessory data for the consumer app.
  Depends on `openpyxl` and (optionally) `Pillow`. Spreadsheet-originated
  values are JSON/HTML escaped before being emitted, but the script still
  assumes DreamFinder templates and should not be used for procurement
  output.
- `create_template.py` generates the DreamFinder retailer onboarding
  `.xlsx` template. Writes to `../onboarding/`, a layout that does
  not exist in this repo. Depends on `openpyxl`.
- `md_to_pdf.py` renders DreamFinder onboarding markdown to PDF.
  References `onboarding/Onboarding_Guide.md`, `Build_Runbook.md`,
  and `Drive_Folder_README.txt` — none of which exist here. Depends
  on `markdown` and `weasyprint`.
- `strip-bg.py` builds an alpha channel from luminance to convert
  white-background JPGs to transparent PNGs. Depends on `Pillow`.

If you are working on procurement, ignore everything in this folder.
If you have confirmed nothing external still depends on these files,
delete the folder.
