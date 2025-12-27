import os
import json
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# Load env from frontend directory where we just created it
load_dotenv(dotenv_path="../frontend/.env.local")

url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # We need the service role key for migration inserts

if not url or not key:
    print("Error: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    print("Please add SUPABASE_SERVICE_ROLE_KEY to your frontend/.env.local (find it under Settings -> API -> service_role in Supabase)")
    exit(1)

supabase: Client = create_client(url, key)

def migrate_links():
    """Migrate links_*.json files if they exist."""
    data_dir = "../data"
    if not os.path.exists(data_dir):
        return

    for file in os.listdir(data_dir):
        if file.startswith("links_") and file.endswith(".json"):
            with open(os.path.join(data_dir, file), 'r') as f:
                links = json.load(f)
                print(f"Migrating {len(links)} links from {file}...")
                # Note: We might want a separate table for links or just store them as raw metadata in reports
                # For this phase, we'll focus on the actual parsed reports.

def migrate_csv():
    """Migrate sso_reports_*.csv files."""
    # This will be implemented once we have the CSV files or after we run the new parser.
    pass

if __name__ == "__main__":
    print("Migration script ready. Please ensure you have the service_role key.")
