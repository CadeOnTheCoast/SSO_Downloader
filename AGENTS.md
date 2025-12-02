# Guidance for AI agents and contributors

This repository automates collecting and parsing Alabama ADEM Sanitary Sewer Overflow (SSO) reports.

## Mental model
- **Scraper/downloader (`SSODownloadOnly.py`):** Uses Playwright to query ADEM's eFile portal for a target year, writes link metadata to `links_<YEAR>.json`, and downloads PDFs into `DOWNLOAD_DIR`. An inline parser call is present but commented out.
- **Parser (`SSO_Parse.py`):** Walks a folder of PDFs, extracts SSO fields, de-duplicates by SSO ID (keeping the newest by footer timestamp), disambiguates receiving waters shared by multiple utilities, and writes a CSV.
- Read these two scripts first before making behavioral changes; there are no deeper packages.

## Conventions and expectations
- Keep configuration flexible: prefer env vars and CLI args over hard-coded paths. Preserve the ability to run different years and paths without code edits.
- Do not wrap imports in try/except. Add logging instead of silently ignoring errors in scraping/parsing flows.
- Follow the current CSV schema in `SSO_Parse.py` unless requirements change; document any schema changes.

## QA/QC workflow for changes
1. Run the downloader on a small date window or single year to produce a controlled set of PDFs and `links_<YEAR>.json`.
2. Run the parser on that set and capture baseline metrics (PDF count, rows kept after de-duplication, rows missing critical fields).
3. Implement focused changes in a branch.
4. Re-run on the same sample and compare outputs (row counts, field completeness, and any parsing failures). Avoid changes that increase failures without justification.
5. Spot-check a few PDFs to confirm critical fields (SSO ID, start/stop, volume, receiving water) still parse correctly.

## Safe-change guidelines
- Before editing, read the relevant script and confirm assumptions from the code, not just the README.
- Prefer incremental changes over large refactors; keep behavioral changes separate from documentation-only edits.
- Maintain multi-year support and configurable paths; avoid hard-coding user-specific directories.
- After changes, rerun QA/QC steps and update docs if behavior or configuration surfaces change. Include a concise commit message summarizing the change.

## Future task ideas
- Extract shared parsing helpers into a small module to reduce duplication between scripts.
- Add lightweight unit tests for parsing functions using sample PDF text snippets.
- Improve robustness for scanned PDFs (e.g., rotation handling, preprocessing before OCR) and add clearer error reporting for parse failures.
