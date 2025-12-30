import os
import logging
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend", "src"))
from parser import SSOParser
from models import SSOReportCreate

# Load credentials
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, "frontend", ".env.local")
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Supabase credentials not found.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
logging.basicConfig(level=logging.INFO)

def process_and_upload():
    parser = SSOParser()
    pdf_dir = os.path.join(base_dir, "data", "pdfs")
    
    if not os.path.exists(pdf_dir):
        logging.error(f"PDF directory not found at: {pdf_dir}")
        return

    pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
    logging.info(f"Found {len(pdf_files)} PDFs in {pdf_dir}")

    for filename in pdf_files[:5]: # Start with a small batch for verification
        path = os.path.join(pdf_dir, filename)
        logging.info(f"Processing {filename}...")
        
        report = parser.process_file(path)
        if report:
            try:
                # Add file metadata
                report_dict = report.model_dump(exclude_none=True)
                report_dict["raw"]["file_name"] = filename
                
                # Upsert to Supabase
                data, count = supabase.table("sso_reports").upsert(
                    report_dict,
                    on_conflict="sso_id"
                ).execute()
                logging.info(f"Successfully uploaded {report.sso_id}")
            except Exception as e:
                logging.error(f"Failed to upload {filename}: {e}")

if __name__ == "__main__":
    process_and_upload()
