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
import sys
import time
from dataclasses import dataclass
from typing import List, Dict

import warnings
warnings.filterwarnings("ignore")

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
DOWNLOAD_DIR = "/Users/cade/SSOs"
LINKS_JSON = "links.json"
CSV_OUTPUT = "/Users/cade/SSOs/sso_reports_2024.csv"
PAGE_LIMIT: int | None = None  # set to an int to stop after N pages; None means no limit

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

    def sanitize_filename(name: str) -> str:
        return re.sub(r"[^\w\-\. ]", "", name).replace(" ", "")

    with sync_playwright() as pw:
        import sys
        DEV_MODE = "--show" in sys.argv
        browser = pw.chromium.launch(headless=not DEV_MODE, slow_mo=250 if DEV_MODE else 0)
        page = browser.new_page()
        page.goto(BASE_URL)

        page.wait_for_selector("input[id$='DateRangeCheckBox']", timeout=10000)
        page.click("input[id$='DateRangeCheckBox']")
        page.wait_for_selector("input[name='ctl00$ContentPlaceHolder1$StartDateTextBox']", timeout=10000)
        page.wait_for_selector("input[name='ctl00$ContentPlaceHolder1$EndDateTextBox']", timeout=10000)

        page.evaluate(f"""
            let el = document.getElementById('ctl00_ContentPlaceHolder1_StartDateTextBox');
            el.removeAttribute('readonly');
            el.value = '{START_DATE}';
        """)
        page.evaluate(f"""
            let el = document.getElementById('ctl00_ContentPlaceHolder1_EndDateTextBox');
            el.removeAttribute('readonly');
            el.value = '{END_DATE}';
        """)
        time.sleep(1)

        # Step 4: Click the "Custom Query" checkbox
        page.evaluate("""
            document.getElementById("ctl00_ContentPlaceHolder1_CheckBoxCustomQuery").click();
        """)
        time.sleep(2)  # allow time for postback

        # Step 5: Select "SSO" in the ListBoxTypes
        page.select_option("#ctl00_ContentPlaceHolder1_ListBoxTypes", value="SSO")
        time.sleep(0.5)

        # Step 5.5: Check the "Water" media area checkbox
        page.check("#ctl00_ContentPlaceHolder1_LibraryCheckBoxList_2")
        time.sleep(0.5)

        # Step 6: Click the "Add Type" button
        page.click("#ctl00_ContentPlaceHolder1_ButtonAddType")
        time.sleep(1)

        # Step 7: Click the "Search" button
        page.click("#ctl00_ContentPlaceHolder1_SearchButton")
        time.sleep(5)  # wait for results to load

        page.wait_for_selector("table#ctl00_ContentPlaceHolder1_DocsGridView")

        page_num = 1
        # Maintain a dict to track counts per facility-date for unique filenames
        filename_counters = {}

        while True:
            logging.info("Reading result page %s", page_num)
            rows = page.query_selector_all(
                "table#ctl00_ContentPlaceHolder1_DocsGridView tbody tr")[2:]
            if not rows:
                break
            for row in rows:
                cells = row.query_selector_all("td")
                if len(cells) < 2:
                    continue  # skip malformed rows

                link_el = cells[0].query_selector("a")
                if not link_el:
                    continue
                # DEBUG: log raw hrefs coming from the table
                raw_href = link_el.get_attribute("href")
                print(f"[DEBUG] raw href on page {page_num}: {raw_href[:120] if raw_href else 'None'}")
                # Skip pager rows or any link that is not a direct DocView URL
                if (raw_href is None) or raw_href.lower().startswith("javascript:"):
                    continue

                metadata = {
                    "master_id": cells[1].inner_text().strip() if len(cells) > 1 else "",
                    "facility": cells[2].inner_text().strip() if len(cells) > 2 else "",
                    "permit": cells[3].inner_text().strip() if len(cells) > 3 else "",
                    "county": cells[4].inner_text().strip() if len(cells) > 4 else "",
                    "date": cells[5].inner_text().strip() if len(cells) > 5 else "",
                    "type": cells[6].inner_text().strip() if len(cells) > 6 else "",
                }
                facility_raw = metadata.get('facility', 'unknown')
                date_raw = metadata.get('date', 'unknown')
                facility_safe = sanitize_filename(facility_raw)
                date_safe = date_raw.replace("/", "-")

                # Create unique filename with counter for multiple SSOs same day and facility
                key = (facility_safe, date_safe)
                count = filename_counters.get(key, 0)
                base_file_name = f"{facility_safe}_{date_safe}_SSO"
                if count > 0:
                    file_name = f"{base_file_name}_{count}.pdf"
                else:
                    file_name = f"{base_file_name}.pdf"

                # Increment counter until file does not exist
                while os.path.exists(os.path.join(DOWNLOAD_DIR, file_name)):
                    count += 1
                    file_name = f"{base_file_name}_{count}.pdf"
                filename_counters[key] = count + 1

                # Only read the <a> element’s href, do not click or expect download
                href = link_el.get_attribute("href") or ""
                if href and not href.lower().startswith("http"):
                    href = "https://app.adem.alabama.gov/eFile/" + href.lstrip("/")
                links.append(DocLink(href, file_name, metadata))

            # always scroll to the bottom so the pager is in view
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(0.5)  # let the pager render
            # ---- pagination ----
            next_page_num = page_num + 1
            clicked = False

            # 1) explicit numbered link by href, e.g. ...Page$2
            link_selector = f"a[href*='Page${next_page_num}']"
            num_link = page.query_selector(link_selector)

            # 2) if the numbered link is not an <a> (because the current page is wrapped
            #    in <span>) we try the visible‑text variant.
            if not num_link:
                num_link = page.query_selector(f"a:has-text('{next_page_num}')")

            # 3) finally try the “Next >” link.
            if not num_link and page.query_selector("a:has-text('Next >')"):
                num_link = page.query_selector("a:has-text('Next >')")

            if num_link and num_link.is_enabled():
                num_link.click(force=True)
                # wait for the next page of results to appear (first data row)
                page.wait_for_selector("table#ctl00_ContentPlaceHolder1_DocsGridView tbody tr:nth-child(3)",
                                        timeout=30000)
                page_num += 1
                if PAGE_LIMIT and page_num > PAGE_LIMIT:
                    logging.info("Reached PAGE_LIMIT=%s, stopping.", PAGE_LIMIT)
                    break
                continue
            else:
                # logging.info("Reached PAGE_LIMIT=%s, stopping.", PAGE_LIMIT)
                if PAGE_LIMIT and page_num >= PAGE_LIMIT:
                    logging.info("Reached PAGE_LIMIT=%s, stopping.", PAGE_LIMIT)
                logging.info("No further pages found after page %s", page_num)
                break

        browser.close()

    with open(LINKS_JSON, "w") as fh:
        json.dump([l.__dict__ for l in links], fh, indent=2)
    logging.info("Found %d documents", len(links))
    return links


def download_pdfs(links: List[DocLink], limit: int = None) -> None:
    """Download each PDF to ``DOWNLOAD_DIR`` using Playwright."""
    import sys
    with sync_playwright() as pw:
        DEV_MODE = "--show" in sys.argv
        browser = pw.chromium.launch(headless=not DEV_MODE, slow_mo=250 if DEV_MODE else 0)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        count = 0
        for link in links:
            if limit is not None and count >= limit:
                break
            # skip javascript: links
            if link.url.lower().startswith("javascript:"):
                continue
            dest = os.path.join(DOWNLOAD_DIR, link.file_name)
            if os.path.exists(dest):
                continue
            logging.info("Downloading %s", dest)
            try:
                page.goto(link.url, timeout=60000)
                # Wait for the download button to be visible
                page.wait_for_selector("#STR_DOWNLOAD", timeout=30000, state="visible")
                with page.expect_download() as download_info:
                    page.click("#STR_DOWNLOAD")
                download = download_info.value
                download.save_as(dest)
                count += 1
                time.sleep(0.5)
            except Exception as e:
                logging.warning("Failed to download %s: %s", link.url, e)
        context.close()
        browser.close()


def parse_pdf_text(text: str) -> Dict[str, str]:
    """Extract key fields from raw text."""
    regex = {
        "permit_number": r"Permit Number\s+([A-Z0-9]+)",
        "permittee": r"Permittee\s+([A-Za-z0-9 ,.&\-]+)",
        "facility_name": r"Facility Name\s+(.+?)\s+Facility County",
        "facility_county": r"Facility County\s+(\w+)",
        "sso_id": r"Assigned SSO ID\s+SSO-(\d+)",
        "volume": r"Estimated Volume Discharged \(in gallons\)\s+([\d,<> to]+)",
        "volume_range": r"Estimated Volume Discharged \(Range\)\s*[\d,<=> ]*gallons\s*<=\s*([\d,]+)",
        "source": r"Indicate source of discharge event\s+(.+?)\s+County in which",
        "latitude": r"Latitude/Longitude of discharge\s+([\d\.\-]+),",
        "longitude": r"Latitude/Longitude of discharge\s+[\d\.\-]+,\s*([\d\.\-]+)",
        "address": r"Street Address\s+(.+)",
        "city": r"City\s+(.+?),",
        "state": r"State\s+([A-Z]{2})",
        "zip": r"ZIP Code\s+(\d+)",
        "location_desc": r"Location Description\s+(.+?)\s+Known or suspected cause",
        "cause": r"Known or suspected cause of the discharge\s+(.+?)\s+Destination of discharge",
        "destination": r"Destination of discharge\s+(.+?)\s+Note:",
        "receiving_water": r"Provide the first named creek or river that receives the flow.\s+(.+?)\s+Did the discharge",
        "corrective_action": r"Describe corrective actions taken.*?\n(.+?)\nPlease attach",
        "public_notice": r"Indicate efforts to notify public.*?\n(.+?)\nDate signs were placed:",
        "signs_date": r"Date signs were placed:\s+([\d/]+)",
        "health_notified": r"County Health Department notification date:\s+([\d/]+)",
    }
    data = {}
    for key, pat in regex.items():
        if key == "volume":
            m = re.search(regex["volume"], text, flags=re.IGNORECASE | re.DOTALL)
            if m:
                vol_str = m.group(1).strip()
                # If volume string contains range indicators, set to 9999
                if '<' in vol_str or 'to' in vol_str.lower():
                    data["volume"] = "9999"
                else:
                    data["volume"] = vol_str
            else:
                m = re.search(regex["volume_range"], text, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    data["volume"] = m.group(1).strip()
                else:
                    data["volume"] = "9999"
        elif key == "volume_range":
            continue
        else:
            m = re.search(pat, text, flags=re.IGNORECASE | re.DOTALL)
            data[key] = m.group(1).strip() if m else None

    # Parse start and stop datetime from the "SSO Event - Information" section
    # Locate the section first
    sso_info_match = re.search(r"SSO Event - Information\s*(.*?)\n\n", text, flags=re.IGNORECASE | re.DOTALL)
    sso_section = sso_info_match.group(1) if sso_info_match else text

    # Extract start date/time
    start_match = re.search(
        r"Date/Time SSO Event Started:\s*Date Time\s*([\d/]+)\s*([\d:]+\s*[apmAPM]{2})",
        sso_section,
        flags=re.IGNORECASE,
    )
    if start_match:
        data["start"] = f"{start_match.group(1)} {start_match.group(2)}"
        data["start_date"] = start_match.group(1)
        data["start_time"] = start_match.group(2)
    else:
        data["start"] = None
        data["start_date"] = None
        data["start_time"] = None

    # Extract stop date/time
    stop_match = re.search(
        r"Date/Time SSO Event Stopped:\s*Date Time\s*([\d/]+)\s*([\d:]+\s*[apmAPM]{2})",
        sso_section,
        flags=re.IGNORECASE,
    )
    if stop_match:
        data["stop"] = f"{stop_match.group(1)} {stop_match.group(2)}"
        data["stop_date"] = stop_match.group(1)
        data["stop_time"] = stop_match.group(2)
    else:
        data["stop"] = None
        data["stop_date"] = None
        data["stop_time"] = None

    # Clean up address parsing: extract address block and parse components
    # Adjust regex to allow multiline and irregular spacing between fields
    address_block_match = re.search(
        r"Street Address\s*\n*\s*(.+?)\s*\n*\s*City\s*\n*\s*(.+?),\s*\n*\s*State\s*\n*\s*([A-Z]{2})\s*\n*\s*ZIP Code\s*\n*\s*(\d+)\s*\n*\s*Location Description\s*\n*\s*(.+?)\s*\n*\s*Known or suspected cause",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if address_block_match:
        data["address"] = address_block_match.group(1).strip()
        data["city"] = address_block_match.group(2).strip()
        data["state"] = address_block_match.group(3).strip()
        data["zip"] = address_block_match.group(4).strip()
        data["location_desc"] = address_block_match.group(5).strip()
    else:
        # fallback to individual regex if block not found
        if not data.get("address"):
            addr_m = re.search(r"Street Address\s+(.+?)\s+City", text, flags=re.IGNORECASE | re.DOTALL)
            if addr_m:
                data["address"] = addr_m.group(1).strip()
        if not data.get("city"):
            city_m = re.search(r"City\s+(.+?),", text, flags=re.IGNORECASE)
            if city_m:
                data["city"] = city_m.group(1).strip()
        if not data.get("zip"):
            zip_m = re.search(r"ZIP Code\s+(\d+)", text, flags=re.IGNORECASE)
            if zip_m:
                data["zip"] = zip_m.group(1).strip()
        if not data.get("location_desc"):
            loc_m = re.search(r"Location Description\s+(.+?)\s+Known or suspected cause", text, flags=re.IGNORECASE | re.DOTALL)
            if loc_m:
                data["location_desc"] = loc_m.group(1).strip()

    # Remove old keys no longer needed
    for old_key in ["start_date", "start_time", "stop_date", "stop_time"]:
        data.pop(old_key, None)

    return data


def parse_pdfs(input_dir: str = DOWNLOAD_DIR) -> None:
    """Parse each downloaded PDF and write a CSV."""
    records = []
    processed_files = set()

    # Skip parsing if output CSV already has data
    if os.path.exists(CSV_OUTPUT):
        try:
            existing_df = pd.read_csv(CSV_OUTPUT)
            processed_files = set(existing_df['file_name'].dropna().unique())
        except Exception:
            pass

    pdf_files = sorted(
        f for f in os.listdir(input_dir)
        if f.lower().endswith(".pdf") and not f.startswith(".")
    )

    for pdf_name in pdf_files:
        if pdf_name in processed_files:
            continue

        path = os.path.join(input_dir, pdf_name)
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                if not pdf.pages:
                    continue
                for page in pdf.pages:
                    try:
                        text += page.extract_text(layout=True) or ""
                    except Exception as e:
                        logging.warning("Text extraction error in %s: %s", pdf_name, e)
        except Exception as e:
            try:
                images = convert_from_path(path)
                if images:
                    text = pytesseract.image_to_string(images[0])
            except Exception as ex:
                logging.warning("OCR failed on %s: %s", pdf_name, ex)
                continue

        record = parse_pdf_text(text)
        record["file_name"] = pdf_name
        records.append(record)

        if len(records) % 10 == 0:
            df_partial = pd.DataFrame(records)
            df_partial.to_csv(CSV_OUTPUT, mode='a', header=not os.path.exists(CSV_OUTPUT), index=False)
            records.clear()

    if records:
        df = pd.DataFrame(records)
        df.to_csv(CSV_OUTPUT, mode='a', header=not os.path.exists(CSV_OUTPUT), index=False)

    logging.info("CSV written to %s", CSV_OUTPUT)


if __name__ == "__main__":
    ensure_dirs()
    links = scrape_links()
    download_pdfs(links)        # download all found PDFs
    # parse_pdfs("/Users/cade/SSOs")
    logging.info("Done")
