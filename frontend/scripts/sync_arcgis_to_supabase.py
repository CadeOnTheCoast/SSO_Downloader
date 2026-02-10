import os
import sys
import logging
import time
from datetime import date, timedelta
from typing import List, Dict, Any

# Add paths
script_dir = os.path.dirname(os.path.abspath(__file__))
# backend src for models
sys.path.append(os.path.join(script_dir, "..", "backend", "src"))

from dotenv import load_dotenv
from supabase import create_client, Client

# Import local modules
from sso_client import SSOClient, SSOQuery
from models import SSOReportCreate
from sso_volume import parse_est_volume

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load env (prioritize root)
root_dir = os.path.dirname(os.path.dirname(script_dir))
env_paths = [
    os.path.join(root_dir, ".env.local"),
    os.path.join(os.path.dirname(script_dir), ".env.local"),
]

for p in env_paths:
    if os.path.exists(p):
        logger.info(f"Loading env from: {p}")
        load_dotenv(p, override=True)
        break

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing Supabase credentials.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert_record(r: dict) -> dict:
    """Convert an ArcGIS SSORecord dict to a Supabase model dict."""
    # Logic to match sso_reports schema
    # parse volume
    vol_gal, _, _ = parse_est_volume(r.get("est_volume"))
    
    # Coordinate validation
    # Coordinate validation
    x = r.get("x") or r.get("long")
    y = r.get("y") or r.get("lat")
    if x == 0 or y == 0: 
        x, y = None, None

    sso_id_val = r.get("sso_id") or r.get("object_id")
    if sso_id_val is None:
        sso_id_val = f"UNKNOWN-{int(time.time()*1000)}"

    return {
        "sso_id": str(sso_id_val),
        "utility_id": r.get("permit"),
        "utility_name": r.get("permittee"),
        "sewer_system": r.get("sewer_system"),
        "county": r.get("county"),
        "location_desc": r.get("location") or r.get("LOCATION_OF_DISCHARGE"),
        "date_sso_began": r.get("date_sso_began"),
        "date_sso_stopped": r.get("date_sso_stopped"),
        "volume_gallons": vol_gal,
        "est_volume": str(r.get("est_volume") or ""),
        "est_volume_gal": int(vol_gal) if vol_gal is not None else None,
        "cause": r.get("cause"),
        "receiving_water": r.get("rec_stream"),
        "x": x,
        "y": y,
        "raw": r # Store full record for safety
    }

def sync_year(year: int):
    client = SSOClient()
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    
    logger.info(f"Syncing year {year}...")
    query = SSOQuery(start_date=start_date, end_date=end_date)
    
    try:
        records = client.fetch_ssos(query)
        if not records:
            logger.info(f"No records found for {year}.")
            return

        logger.info(f"Found {len(records)} records for {year}. Preparing upsert...")
        
        batch_size = 100
        upserted_count = 0
        
        # Prepare batch
        batch = []
        for r in records:
            # client.fetch_ssos returns objects or dicts? sso_client says returns List[Dict] in fetch_ssos.
            # But earlier verify script treated them as objects? No, verify check `isinstance(r, dict)`.
            # `fetch_ssos` implementation (read via view_file) returns `records: List[Dict[str, Any]]`.
            # So `r` is a dict.
            data = convert_record(r)
            # Validate with Pydantic
            try:
                model = SSOReportCreate(**data)
                batch.append(model.model_dump(exclude_none=True, mode='json'))
            except Exception as e:
                logger.warning(f"Validation failed for record {r.get('sso_id')}: {e}")
            
            if len(batch) >= batch_size:
                # Upsert
                try:
                    res, count = supabase.table("sso_reports").upsert(batch, on_conflict="sso_id").execute()
                    upserted_count += len(batch)
                    batch = []
                except Exception as e:
                    logger.error(f"Batch upsert failed: {e}")
                    batch = [] # Drop batch to continue? Or retry? For now continue.

        # Final batch
        if batch:
             try:
                res, count = supabase.table("sso_reports").upsert(batch, on_conflict="sso_id").execute()
                upserted_count += len(batch)
             except Exception as e:
                logger.error(f"Final batch upsert failed: {e}")

        logger.info(f"Synced {upserted_count}/{len(records)} records for {year}.")
        
    except Exception as e:
        logger.error(f"Failed to sync {year}: {e}")

def main():
    # Sync last 10 years + current + next (failures/future dates)
    current_year = date.today().year
    years = range(2012, current_year + 2) 
    
    for y in years:
        sync_year(y)

if __name__ == "__main__":
    main()
