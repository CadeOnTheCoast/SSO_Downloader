#!/usr/bin/env python3
"""Automated SSO PDF downloader and parser.

This script scrapes Alabama's ADEM eFile site for all Sanitary Sewer Overflow
(SSO) reports filed in 2024, downloads the PDF documents, extracts key fields
and writes the results to ``sso_reports_2024.csv``.
"""

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import List, Dict

import pandas as pd
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from playwright.sync_api import sync_playwright
import requests

# Constants
BASE_URL = "https://app.adem.alabama.gov/eFile/Default.aspx"
START_DATE = "01/01/2024"
END_DATE = "12/31/2024"
DOWNLOAD_DIR = "downloads"
LINKS_JSON = "links.json"
CSV_OUTPUT = "sso_reports_2024.csv"

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def ensure_dirs() -> None:
    """Ensure that the download folder exists."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@dataclass
class DocLink:
    url: str
    file_name: str
    metadata: Dict[str, str]


def scrape_links() -> List[DocLink]:
    """Use Playwright to collect PDF links for 2024 SSO reports."""
    logging.info("Scraping document links from eFile")
    links: List[DocLink] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL)

        # enable date range
        page.check("input[id$='DateRangeCheckBox']")
        page.evaluate(
            f"document.getElementById('ctl00_ContentPlaceHolder1_txtStartDate').value='{START_DATE}';")
        page.evaluate(
            f"document.getElementById('ctl00_ContentPlaceHolder1_txtEndDate').value='{END_DATE}';")
        page.click("[id$='ddlDocumentTypes_Input']")
        page.fill("[id$='ddlDocumentTypes_Input']", "SSO")
        page.click("input[id$='SearchButton']")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("table#ctl00_ContentPlaceHolder1_DocsGridView")

        page_num = 1
        while True:
            logging.info("Reading result page %s", page_num)
            rows = page.query_selector_all(
                "table#ctl00_ContentPlaceHolder1_DocsGridView tbody tr")[2:]
            if not rows:
                break
            for row in rows:
                cells = row.query_selector_all("td")
                link = cells[0].query_selector("a")
                url = link.get_attribute("href")
                fname = cells[7].inner_text().strip()
                metadata = {
                    "master_id": cells[1].inner_text().strip(),
                    "facility": cells[2].inner_text().strip(),
                    "permit": cells[3].inner_text().strip(),
                    "county": cells[4].inner_text().strip(),
                    "date": cells[5].inner_text().strip(),
                    "type": cells[6].inner_text().strip(),
                }
                links.append(DocLink(url, fname, metadata))
            # next page
            page_num += 1
            try:
                page.click(f"table#ctl00_ContentPlaceHolder1_DocsGridView a:has-text('{page_num}')")
                page.wait_for_load_state("networkidle")
            except Exception:
                break

        browser.close()

    with open(LINKS_JSON, "w") as fh:
        json.dump([l.__dict__ for l in links], fh, indent=2)
    logging.info("Found %d documents", len(links))
    return links


def download_pdfs(links: List[DocLink]) -> None:
    """Download each PDF to ``DOWNLOAD_DIR``."""
    session = requests.Session()
    for link in links:
        dest = os.path.join(DOWNLOAD_DIR, link.file_name)
        if os.path.exists(dest):
            continue
        logging.info("Downloading %s", dest)
        r = session.get(link.url)
        if r.status_code == 200:
            with open(dest, "wb") as fh:
                fh.write(r.content)
            time.sleep(0.5)
        else:
            logging.warning("Failed to download %s", link.url)


def parse_pdf_text(text: str) -> Dict[str, str]:
    """Extract key fields from raw text."""
    regex = {
        "sso_id": r"(SSO-\d{8})",
        "start": r"Start\s*Date/Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)",
        "stop": r"Stop\s*Date/Time[:\s]*(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\s*(?:am|pm)?)",
        "volume": r"Estimated\s*Volume[:\s]*([\d,\.]+)\s*(gallons?)",
        "report_type": r"Report\s*Type[:\s]*([\w\s-]+)",
    }
    data = {}
    for key, pat in regex.items():
        m = re.search(pat, text, flags=re.IGNORECASE)
        data[key] = m.group(1).strip() if m else None
    return data


def parse_pdfs() -> None:
    """Parse each downloaded PDF and write a CSV."""
    records = []
    for pdf_name in os.listdir(DOWNLOAD_DIR):
        if not pdf_name.lower().endswith(".pdf"):
            continue
        path = os.path.join(DOWNLOAD_DIR, pdf_name)
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception:
            images = convert_from_path(path)
            for img in images:
                text += pytesseract.image_to_string(img)
        record = parse_pdf_text(text)
        record["file_name"] = pdf_name
        records.append(record)

    df = pd.DataFrame(records)
    df.to_csv(CSV_OUTPUT, index=False)
    logging.info("CSV written to %s", CSV_OUTPUT)


if __name__ == "__main__":
    ensure_dirs()
    links = scrape_links()
    download_pdfs(links)
    parse_pdfs()
    logging.info("Done")
