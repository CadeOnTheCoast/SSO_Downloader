# ADEM Sanitary Sewer Overflow (SSO) Downloader and Parser

Scrape SSO reports from ADEM's eFile portal for a date range, download the PDFs, and parse key fields into a CSV for analysis or QA/QC. Use it when you need a reproducible pull of ADEM SSO reports for a specific year or to re-parse an existing set of PDFs with consistent logic.

## Repository layout and entry points

- **Scrape + download:** `SSODownloadOnly.py`
  - Collects SSO document links for a year, saves them to `links_<YEAR>.json`, and downloads PDFs into `DOWNLOAD_DIR`.
  - Has an optional (commented) call to parse the downloaded PDFs in the same run.
- **Parse existing PDFs:** `SSO_Parse.py`
  - Walks a folder of PDFs, de-duplicates by SSO ID (keeping the newest by footer timestamp), disambiguates waterbodies, and writes a CSV.
- **Legacy artifacts:** `links_2022.json` and `links_2023.json` are example scrape outputs and can be used as references for expected metadata.

## Requirements and installation

- **Python:** 3.10+
- **System dependencies:**
  - [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (used when PDFs are scanned images)
  - [Poppler](https://poppler.freedesktop.org/) utilities (needed by `pdf2image` for OCR fallback)
  - Playwright browser runtime (Chromium)
- **Python packages:** `playwright pdfplumber pdf2image pytesseract pandas requests`

### Install system packages

macOS (Homebrew):
```bash
brew install tesseract poppler
```

Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

### Install Python dependencies

```bash
pip install -r requirements.txt  # if you maintain one
# or
pip install playwright pdfplumber pdf2image pytesseract pandas requests
python -m playwright install chromium
```

## Configuration

### Scrape and download (`SSODownloadOnly.py`)
- **Year selection:**
  - Default: `DEFAULT_YEAR = 2023`
  - Override via `SSO_YEAR` env var or the first CLI arg (e.g., `python SSODownloadOnly.py 2024`).
- **Date range:** Automatically set to `01/01/<YEAR>` through `12/31/<YEAR>`.
- **Paths:**
  - `DOWNLOAD_DIR` (default `/Users/cade/SSOs/<YEAR>`) — change to a writable folder.
  - `LINKS_JSON` (default `links_<YEAR>.json`) — metadata for discovered documents.
  - `CSV_OUTPUT` (default `/Users/cade/SSOs/sso_reports_<YEAR>.csv`) — target CSV if parsing is enabled.
- **Browser mode:** Add `--show` to run Playwright with a visible browser.
- **Page limiting:** `PAGE_LIMIT` can stop pagination early for debugging.
- **Tesseract path:** Adjust `pytesseract.pytesseract.tesseract_cmd` if tesseract is not on PATH.

### Parse existing PDFs (`SSO_Parse.py`)
- **Input/output:**
  - `PDF_DIR` env var or first CLI arg sets the folder to scan (default `/Users/cade/SSOs`).
  - `OUTPUT_CSV` env var or second CLI arg sets the CSV path (default `parsed_sso_data.csv`).
- **Waterbody disambiguation:** Toggle `PRESERVE_RAW_WATERNAME` to retain the original receiving water name in an extra column.

## Usage

### 1) Scrape and download a year of SSO PDFs
```bash
SSO_YEAR=2024 python SSODownloadOnly.py
# or
python SSODownloadOnly.py 2024
```
Outputs:
- PDFs in `DOWNLOAD_DIR`
- Link metadata in `links_<YEAR>.json`
- Enable the inline parser by uncommenting `parse_pdfs(DOWNLOAD_DIR)` near the end of the script if you want CSV generation in the same run.

### 2) Parse a folder of PDFs into CSV
```bash
PDF_DIR=/path/to/pdfs OUTPUT_CSV=/path/to/output.csv python SSO_Parse.py
# or
python SSO_Parse.py /path/to/pdfs /path/to/output.csv
```
Outputs:
- CSV at `OUTPUT_CSV`
- Console summary of PDF count, rows kept after de-duplication, and rows missing critical fields.

## Output schema (SSO_Parse)

Columns written in `OUTPUT_CSV`:
- Identifiers: `sso_id`, `file_name`
- Permittee/facility: `permittee`, `facility`
- Timing: `start`, `stop`
- Volume: `volume` (upper bound used if a range; `9999` when the form indicates a range but no values are present)
- Location/hydrology: `receiving_water` (optionally raw value), `latitude`, `longitude`, `destination`
- Impact/response: `swimming_water`, `monitoring`, `cleaned`, `disinfected`
- Cause: `cause`

Behavioral notes:
- **De-duplication:** Rows are keyed by `sso_id`; if missing, the file name is used. The most recent PDF (by footer timestamp) is kept.
- **Waterbody disambiguation:** If multiple permittees share a receiving water name, the script appends a short utility tag (e.g., `– BCSS`).
- **OCR fallback:** If text extraction fails, the parser renders pages with `pdf2image` and runs Tesseract OCR.

## QA/QC checklist
- Compare the number of PDFs in `PDF_DIR` to the number of CSV rows after de-duplication; small differences are expected only when multiple PDFs share an SSO ID.
- Spot-check a few PDFs: confirm `sso_id`, event start/stop, volume, and receiving water match the form.
- Verify every PDF filename appears in the CSV (except intentional de-duplication cases).
- Review rows where critical fields (`sso_id`, `start`, `volume`) are missing; these often correspond to scanned/poor-quality PDFs.

## Troubleshooting
- **No results or empty `links_<YEAR>.json`:** Confirm the year/date range and that ADEM eFile selectors (IDs in `scrape_links`) still match the site.
- **Playwright navigation errors:** Re-run with `--show` to observe the UI; update selectors if the site changed.
- **Missing PDFs:** Check write permissions to `DOWNLOAD_DIR` and network stability; downloads rely on Playwright's `#STR_DOWNLOAD` button.
- **Parsing misses fields:** Ensure Tesseract and Poppler are installed and accessible; scanned PDFs depend on OCR.
- **Poor OCR output:** Rerun just the parser on affected files after improving OCR (better Poppler build, updated Tesseract language data, or manual cleanup).

## Future work
- Add CLI flags for output paths and date ranges to avoid hard-coded constants.
- Extract shared parsing logic into reusable modules and add unit tests for common form patterns.
- Improve handling of scanned PDFs (e.g., adaptive thresholds, rotated pages) and add structured logging for parse failures.
