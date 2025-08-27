# ADEM Sanitary Sewer Overflow (SSO) 2024 Scraper and Parser

Scrape SSO reports from ADEM’s eFile portal for a given date range (default: calendar year 2024), download the PDFs, and parse key fields into CSV for analysis.

## What this does

1. Searches ADEM eFile for SSO documents within a date range  
2. Saves a list of document links and downloads each PDF  
3. Parses PDFs to extract core SSO fields and writes a CSV

Two entry points are provided:
- `sso_etl.py` runs end to end (link discovery, download, parse)
- `parse_only.py` parses an existing folder of PDFs

## Requirements

- Python 3.10 or newer
- System packages:
  - Tesseract OCR
  - Poppler (for `pdf2image`)

macOS:
```bash
brew install tesseract poppler
```

Ubuntu or Debian:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils
```

### Python dependencies

Install with pip:
```bash
pip install playwright pdfplumber pdf2image pytesseract pandas requests
python -m playwright install chromium
```

## Configuration

Edit the constants at the top of `sso_etl.py` to set your year and paths.

```python
BASE_URL   = "https://app.adem.alabama.gov/eFile/Default.aspx"
START_DATE = "01/01/2024"        # set start of desired range
END_DATE   = "12/31/2024"        # set end of desired range
DOWNLOAD_DIR = "/Users/you/SSOs" # where PDFs are saved
LINKS_JSON   = "links.json"      # metadata for discovered documents
CSV_OUTPUT   = "/Users/you/SSOs/sso_reports_2024.csv"
```

Tesseract path (change if needed):
```python
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
```

Optional page limiter for debugging:
```python
PAGE_LIMIT: int | None = None   # set to an integer to stop after N pages
```

## Usage

### Full scrape and parse

```bash
python sso_etl.py
```

Developer mode with a visible browser:
```bash
python sso_etl.py --show
```

Results:
- PDFs saved to `DOWNLOAD_DIR`
- Discovered links in `links.json`
- Parsed rows appended to `CSV_OUTPUT`

### Parse a folder of PDFs only

If you already have PDFs, set the folder in `parse_only.py`:

```python
PDF_DIR = "/Users/you/SSOs"
OUTPUT_CSV = "parsed_sso_data.csv"
```

Run:
```bash
python parse_only.py
```

The script de-duplicates by `Assigned SSO ID` and keeps the most recent copy based on the PDF footer timestamp.

## Output fields

The parser extracts the following (when present in the document):
- Permit and facility: `permit_number`, `permittee`, `facility_name`, `facility_county`
- Event timing: `start_date`, `start_time`, `stop_date`, `stop_time`
- Location: `latitude`, `longitude`, `address`, `city`, `state`, `zip`, `location_desc`
- Hydrology and impact: `receiving_water`, `destination`, `public_notice`, `signs_date`, `health_notified`
- Cause and response: `source`, `cause`, `corrective_action`
- Volume: `volume` or `volume_range` upper bound
- Identifiers and file info: `sso_id`, `file_name`

Notes on volume:
- If the form reports a single number, that value is used
- If the form reports a range, the upper bound is used when available
- If the form indicates a range but omits values, a sentinel like `9999` is recorded to indicate “range selected, value missing”

## Known Issues

- If an SSO is submitted outside of the e-SSO reporting system (i.e. is scanned and emailed, faxed, etc) the resulting file in e-file usually does not have OCR and the parser will fail to correctly parse it. Those are usually less than 5% of the total SSOs and can be dealt with manually

## Planned Next Steps

### 1. **Robustness and Resilience**
- [ ] **Add error handling**: e.g., when `driver.execute_script()` returns `None` or malformed data.
- [ ] **Detect DOM load/failure**: Use Selenium waits instead of `time.sleep()`.
- [ ] **Handle ChromeDriver path flexibly**: Add logic to detect or prompt for `chromedriver` path.

### 2. **Code Structure**
- [ ] **Package parsing logic into a function in a module** instead of directly importing all globals from `parse_only`.
- [ ] **Use argparse or click**: Let users specify options (e.g., year filter, output path) via CLI.

### 3. **Year Filtering**
- [ ] Currently the filter for `2024` is a simple string search. Consider parsing dates and filtering more formally to make it future-proof.

### 4. **Testing**
- [ ] Add basic test cases for the parser to verify that common input formats yield correct structured outputs.

### 5. **Data Output**
- [ ] Include metadata (e.g., scrape date, source URL) in a separate metadata JSON or README section in the output folder.

### 6. **README Enhancement**
- [ ] Add screenshots or an example row from the CSV to show what output looks like.

## Troubleshooting

- If no results appear, confirm `START_DATE` and `END_DATE`, and that “Custom Query” fields on the site are still named the same; UI changes can require selector updates
- If downloads fail, verify write permissions to `DOWNLOAD_DIR`
- If parsing misses fields, confirm Tesseract is installed and the path is set; scanned PDFs require OCR
- If `pdf2image` errors, ensure Poppler is installed and available on your PATH

## License

MIT
