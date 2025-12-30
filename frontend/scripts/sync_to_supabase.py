import os
import json
import logging
from typing import List, Optional
from pydantic import BaseModel, ValidationError
from supabase import create_client, Client
from dotenv import load_dotenv
import sys

# Add backend/src to path for internal imports
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend", "src"))
from models import SSOReportCreate

logging.basicConfig(level=logging.INFO)

# Load credentials from root-relative path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, "frontend", ".env.local")

if os.path.exists(env_path):
    logging.info(f"Found .env.local at: {env_path}")
    from dotenv import dotenv_values
    found_keys = list(dotenv_values(env_path).keys())
    logging.info(f"Keys found in .env.local: {found_keys}")
    load_dotenv(dotenv_path=env_path)
else:
    logging.error(f".env.local NOT found at: {env_path}")

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

logging.info(f"Checking env: URL={'Found' if SUPABASE_URL else 'Missing'}, KEY={'Found' if SUPABASE_KEY else 'Missing'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error(f"Missing Supabase credentials. Checked path: {env_path}")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO)

def upload_report(report_data: dict):
    """Validate and upload a single report to Supabase."""
    try:
        # Pydantic validation
        report = SSOReportCreate(**report_data)
        
        # Upsert into Supabase (using sso_id as unique constraint in SQL)
        data, count = supabase.table("sso_reports").upsert(
            report.model_dump(exclude_none=True),
            on_conflict="sso_id"
        ).execute()
        
        return True
    except ValidationError as e:
        logging.warning(f"Validation failed for report {report_data.get('sso_id')}: {e}")
        return False
    except Exception as e:
        logging.error(f"Upload failed for report {report_data.get('sso_id')}: {e}")
        return False

def sync_all_json():
    """Sync all links_*.json data to the database."""
    # Use absolute path for data_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(os.path.dirname(script_dir), "data")
    
    if not os.path.exists(data_dir):
        logging.error(f"Data directory NOT found at: {data_dir}")
        return

    for filename in os.listdir(data_dir):
        if filename.startswith("links_") and filename.endswith(".json"):
            path = os.path.join(data_dir, filename)
            with open(path, 'r') as f:
                records = json.load(f)
                logging.info(f"Syncing {len(records)} records from {filename}...")
                success_count = 0
                for rec in records:
                    # Flatten metadata for the DB
                    flat_rec = {
                        "sso_id": rec["metadata"].get("sso_id") or f"LINK-{rec['url'].split('=')[-1]}",
                        "utility_name": rec["metadata"].get("facility"),
                        "utility_id": rec["metadata"].get("permit"),
                        "county": rec["metadata"].get("county"),
                        "raw": rec
                    }
                    if upload_report(flat_rec):
                        success_count += 1
                logging.info(f"Successfully synced {success_count}/{len(records)} from {filename}")

if __name__ == "__main__":
    sync_all_json()
