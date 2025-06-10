#!/usr/bin/env python3
"""
`sso_etl_playwright.py`

Full ETL pipeline using Playwright to scrape, download, and parse SSO PDFs from ADEM eFile into a CSV.
"""
import os
import json
import re
import time
import logging
import requests
import pandas as pd
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from playwright.sync_api import sync_playwright

# --- Configuration ---
BASE_URL     = 'https://app.adem.alabama.gov/eFile/Default.aspx'
START_DATE   = '01/01/2024'
END_DATE     = '12/31/2024'
DOWNLOAD_DIR = 'downloads'
LINKS_JSON   = 'links.json'
CSV_OUTPUT   = 'all_ssos.csv'

# Tesseract path (adjust if necessary)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Logging config
template = '%(asctime)s %(levelname)s %(message)s'
logging.basicConfig(level=logging.INFO, format=template)


def ensure_dirs():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def scrape_links():
    logging.info('Launching headless browser to scrape links')
    all_links = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)
        # Enable date range
        page.wait_for_selector('input[id$="DateRangeCheckBox"]', timeout=15000)
        page.check('input[id$="DateRangeCheckBox"]')
        # Directly set date values via JS and trigger change events
        page.evaluate(f"""(() => {{
            const sd = document.getElementById('ctl00_ContentPlaceHolder1_txtStartDate');
            sd.value = '{START_DATE}';
            sd.dispatchEvent(new Event('change', {{ bubbles: true }}));
            const ed = document.getElementById('ctl00_ContentPlaceHolder1_txtEndDate');
            ed.value = '{END_DATE}';
            ed.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }})()""")
        # Brief pause to allow any Ajax postback to complete
        page.wait_for_timeout(1000)
        # Select SSO type
        page.click('[id$="ddlDocumentTypes_Input"]')
        page.fill('[id$="ddlDocumentTypes_Input"]', 'SSO')
        page.wait_for_timeout(500)
        # Trigger search
        page.click('input[id$="SearchButton"]')
        page.wait_for_load_state('networkidle')

        page_num = 1
        # Wait for the results grid to appear
        page.wait_for_selector('table#ctl00_ContentPlaceHolder1_DocsGridView', timeout=15000)
        while True:
            logging.info(f'Scraping grid page {page_num}')
            # Select all data rows (skip header rows)
            rows = page.query_selector_all('table#ctl00_ContentPlaceHolder1_DocsGridView tbody tr')[2:]
            if not rows:
                break
            for row in rows:
                cells = row.query_selector_all('td')
                link_el = cells[0].query_selector('a')
                all_links.append({
                    'doc_url': link_el.get_attribute('href'),
                    'master_id':   cells[1].inner_text().strip(),
                    'facility':    cells[2].inner_text().strip(),
                    'permit':      cells[3].inner_text().strip(),
                    'county':      cells[4].inner_text().strip(),
                    'date':        cells[5].inner_text().strip(),
                    'type':        cells[6].inner_text().strip(),
                    'file_name':   cells[7].inner_text().strip(),
                })
            # Attempt to go to the next page
            next_page = page_num + 1
            try:
                page.click(f"table#ctl00_ContentPlaceHolder1_DocsGridView a:has-text('{next_page}')")
                page.wait_for_load_state('networkidle')
                page_num += 1
            except Exception:
                break
        browser.close()

    logging.info(f'Total documents found: {len(all_links)}')
    with open(LINKS_JSON, 'w') as f:
        json.dump(all_links, f, indent=2)
    logging.info(f'Links written to {LINKS_JSON}')


def download_pdfs():
    logging.info('Downloading PDFs')
    session = requests.Session()
    with open(LINKS_JSON) as f:
        links = json.load(f)
    for entry in links:
        url = entry['doc_url']
        fname = os.path.join(DOWNLOAD_DIR, entry['file_name'])
        if os.path.exists(fname):
            logging.debug(f'Skipping existing: {fname}')
            continue
        logging.info(f'Downloading {fname}')
        resp = session.get(url)
        if resp.status_code == 200:
            with open(fname, 'wb') as pdf:
                pdf.write(resp.content)
        else:
            logging.warning(f'Failed to download {url}: {resp.status_code}')
        time.sleep(0.5)


def parse_sso_text(text: str) -> dict:
    """
    Extracts key fields from raw SSO text via regex.
    """
    patterns = {
        'sso_id':     r'(SSO-\d{8})',
        'start':      r'Start\s*Date/Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
        'stop':       r'Stop\s*Date/Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)',
        'volume':     r'Estimated\s*Volume[:\s]*([\d,\.]+)\s*(gallons?)',
        'report_type':r'Report\s*Type[:\s]*([\w\s-]+)'
    }
    data = {}
    for key, pat in patterns.items():
        m = re.search(pat, text, flags=re.IGNORECASE)
        data[key] = m.group(1).strip() if m else None
    return data


def parse_pdfs():
    logging.info('Parsing downloaded PDFs')
    records = []
    for fname in os.listdir(DOWNLOAD_DIR):
        if not fname.lower().endswith('.pdf'):
            continue
        path = os.path.join(DOWNLOAD_DIR, fname)
        text = ''
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ''
        except Exception:
            logging.warning(f'OCR fallback for {fname}')
            images = convert_from_path(path)
            for img in images:
                text += pytesseract.image_to_string(img)
        parsed = parse_sso_text(text)
        parsed['file_name'] = fname
        records.append(parsed)

    df = pd.DataFrame(records)
    df.to_csv(CSV_OUTPUT, index=False)
    logging.info(f'All records written to {CSV_OUTPUT}')


if __name__ == '__main__':
    ensure_dirs()
    scrape_links()
    download_pdfs()
    parse_pdfs()
    logging.info('ETL process complete')
