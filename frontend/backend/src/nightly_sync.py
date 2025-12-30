import os
import logging
import sys
import re
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from supabase import create_client, Client

# Add paths for internal imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parser import SSOParser
from models import SSOReportCreate

# Configuration
load_dotenv()
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
BASE_URL = "https://efile.adem.alabama.gov/gis/ssoris/"

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Missing Supabase credentials for nightly sync.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class NightlySyncWorker:
    def __init__(self):
        self.parser = SSOParser()
        self.temp_pdf_dir = "temp_pdfs"
        os.makedirs(self.temp_pdf_dir, exist_ok=True)

    def scrape_new_links(self) -> List[Dict[str, str]]:
        """Scrape the latest SSO links from ADEM eFile."""
        logging.info("Scraping latest links from ADEM...")
        links = []
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(BASE_URL)
            
            # Use current year by default
            year = datetime.now().year
            page.select_option("#ddlYear", str(year))
            page.click("#btnSearch")
            
            # Wait for results and extract
            page.wait_for_selector("#gvResults")
            rows = page.query_selector_all("#gvResults tr:not(.header)")
            for row in rows:
                cols = row.query_selector_all("td")
                if len(cols) >= 3:
                    link_btn = cols[0].query_selector("a")
                    if link_btn:
                        url = link_btn.get_attribute("href")
                        # Format is often javascript:__doPostBack(...) or direct URL
                        # For simplicity, we'll focus on the data ID in the URL if possible
                        links.append({
                            "url": f"https://efile.adem.alabama.gov/gis/ssoris/{url}" if url.startswith("View") else url,
                            "facility": cols[1].inner_text(),
                            "permit": cols[2].inner_text(),
                        })
            browser.close()
        return links

    def get_existing_sso_ids(self) -> set:
        """Fetch existing SSO IDs to avoid duplicates."""
        response = supabase.table("sso_reports").select("sso_id").execute()
        return {r["sso_id"] for r in response.data} if response.data else set()

    def download_pdf(self, url: str, filename: str) -> Optional[str]:
        """Download PDF for parsing."""
        path = os.path.join(self.temp_pdf_dir, filename)
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                with open(path, "wb") as f:
                    f.write(response.content)
                return path
        except Exception as e:
            logging.error(f"Failed to download {url}: {e}")
        return None

    def run(self):
        logging.info("Starting nightly sync worker...")
        all_links = self.scrape_new_links()
        existing_ids = self.get_existing_sso_ids()
        
        new_records_count = 0
        for link in all_links:
            # Extract ID from URL for quick check if possible
            # e.g., ViewReport.aspx?id=12345
            match = re.search(r"id=(\d+)", link["url"])
            if match:
                sso_id = f"SSO-{match.group(1)}"
                if sso_id in existing_ids:
                    continue
            
            # Download and parse
            filename = f"temp_{datetime.now().timestamp()}.pdf"
            pdf_path = self.download_pdf(link["url"], filename)
            
            if pdf_path:
                report = self.parser.process_file(pdf_path)
                if report:
                    try:
                        supabase.table("sso_reports").upsert(
                            report.model_dump(exclude_none=True),
                            on_conflict="sso_id"
                        ).execute()
                        new_records_count += 1
                        logging.info(f"Synced new report: {report.sso_id}")
                    except Exception as e:
                        logging.error(f"Failed to upload {report.sso_id}: {e}")
                
                os.remove(pdf_path) # Cleanup

        logging.info(f"Sync complete. Added {new_records_count} new records.")

if __name__ == "__main__":
    worker = NightlySyncWorker()
    worker.run()
