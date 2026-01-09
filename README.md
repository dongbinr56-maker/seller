# Digital Template Production Pipeline (MVP)

This repository contains a minimal pipeline to generate printable PDF templates, preview images, and metadata from CSV inputs.

## Requirements

```bash
pip install -r requirements.txt
```

## Quick start

```bash
python -m app.main build --csv data/products.csv --out out
```

To retry only failed products:

```bash
python -m app.main retry --failed --out out
```

## Output structure

Each SKU is written under `out/{slug}/` with the following artifacts:

- `product_a4.pdf`
- `product_usletter.pdf`
- `preview_1.png`, `preview_2.png`, `preview_3.png`
- `bundle.zip` (PDFs + README.txt)
- `metadata.json`
- `spec.json`
- `error.log` (only on failure)

The SQLite database is stored at `out/ace.db`.

## Notes

- PDF rendering uses ReportLab.
- Preview rendering uses PyMuPDF (fitz) and does not require poppler.
- If PyMuPDF is missing, install it with `pip install PyMuPDF` and retry.
