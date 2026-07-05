# AI Digital Product Engine

Local-first operating files for turning verified MPC and technical assets into Gumroad-ready products.

This repository tracks the public/storefront side of the business system. It intentionally excludes source DOCX files, raw drafts, generated PDFs, and private product assets.

## Product Catalog

| Product | Price | Type | Status |
| --- | ---: | --- | --- |
| The MPC Codex: First Track Fast | $19 intro / $29 normal | PDF download | Ready for Gumroad upload |
| MPC Library Cleanup Audit | $79 | Manual service | Ready for Gumroad listing |
| MPCLII Vault loop packs | TBD | ZIP loop packs | Pending audio clearance |

## Setup

Required free/local tools:

```bash
brew install pandoc
```

This Mac already has a TeX/XeLaTeX install used by `build_product.py`. If another machine does not, install a free TeX distribution before rebuilding PDFs.

The PDF builder does not require WeasyPrint, Docker, cloud servers, or paid software.

## Rebuild The PDF

The private source files must exist locally first:

- `~/digital-product-engine/drafts/ch01.md`
- `~/digital-product-engine/drafts/ch02.md`

Then run:

```bash
python3 ~/digital-product-engine/build_product.py
```

Output:

```text
~/digital-product-engine/dist/mpc-codex-first-track-fast-v1.pdf
```

## Storefront Workflow

1. Upload the Codex PDF product using `gumroad/mpc-codex-excerpt.json`.
2. Create the audit service listing using `gumroad/mpc-audit-service.json`.
3. Follow `gumroad/upload-checklist.md`.
4. Keep `STOREFRONT.md` updated with final Gumroad URLs.

## Git Safety

Ignored by design:

- `dist/`
- `raw/`
- `drafts/`
- `build/`

Those folders may contain source IP, generated private assets, or rendered products that should not be public by default.
