# Procurement Materials

This folder contains text-based procurement setup materials for Continental Silverline and the reusable mattress bid questionnaire.

## Why the Excel and ZIP files are not committed

The Codex web PR/diff interface does not support binary file previews for `.xlsx` or `.zip` files. To keep the PR reviewable and avoid the "Binary files are not supported" error, the repository stores the questionnaire as CSV plus Markdown documents.

## Files

- `mattress_bid_setup_questionnaire.csv` — spreadsheet-ready questionnaire that can be opened in Excel or imported into Google Sheets.
- `continental_silverline_bid_setup_profile.md` — sanitized public-sector pursuit profile built from the completed questionnaire.
- `step_2_portal_and_commodity_checklist.md` — portal registration, commodity-code, and saved-search checklist.

## How to use the CSV as a spreadsheet

### Excel

1. Download `mattress_bid_setup_questionnaire.csv` from the PR or repository file view.
2. Open Excel.
3. Choose **File → Open** and select the CSV.
4. Save a copy as `.xlsx` if you want an Excel workbook.

### Google Sheets

1. Open Google Sheets.
2. Choose **File → Import → Upload**.
3. Upload `mattress_bid_setup_questionnaire.csv`.
4. Choose **Create new spreadsheet** or **Replace spreadsheet**.

## Optional: recreate a local ZIP package

If you have a local checkout, run:

```bash
python3 tools/create_procurement_package.py
```

That creates `continental_silverline_procurement_files.zip` locally without storing the binary zip in the PR.
