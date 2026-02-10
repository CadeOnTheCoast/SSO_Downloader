import os
import logging
from typing import List, Dict, Any, Optional
from datetime import date, datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Import schema from existing modules
# We need to add scripts folder to path or rely on relative imports if in same package?
# Ideally this file lives in frontend/backend/src alongside api.py?
# Yes, safer to put it in backend/src.

from sso_client import SSOClient, SSOQuery

logger = logging.getLogger(__name__)

class SSODBClient(SSOClient):
    def __init__(self, use_cache: bool = True):
        # Initialize parent (though we override its Main function, it might have helpers)
        super().__init__(use_cache)
        
        # Load env 
        SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
        SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Or ANON if RLS allows
        
        # Fallback for local dev if keys missing in env (assume .env.local loaded by api.py/uvicorn)
        # But if running standalone, might need dotenv. 
        # api.py startup handles loading env usually? 
        # Actually api.py doesn't seem to load .env.local explicitly in code I saw. 
        # Uvicorn or wrapper script does.
             
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase credentials missing in SSODBClient init.")
            self.client = None
        else:
            self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    def fetch_ssos(self, query: SSOQuery, limit: int = 10000) -> List[Dict[str, Any]]:
        if not self.client:
            logger.error("DB Client not initialized, falling back to empty list (or should we fallback to parent?)")
            return []

        # Build query
        db_query = self.client.table("sso_reports").select("*")
        
        # Filters logic... (same as before)
        if query.utility_id:
            db_query = db_query.eq("utility_id", query.utility_id)
        
        if query.permit_ids:
            db_query = db_query.in_("utility_id", query.permit_ids)

        if query.utility_name:
            db_query = db_query.ilike("utility_name", f"%{query.utility_name}%")
            
        if query.county:
             db_query = db_query.eq("county", query.county)
             
        if query.start_date:
            db_query = db_query.gte("date_sso_began", query.start_date.isoformat())
            
        if query.end_date:
             db_query = db_query.lte("date_sso_began", query.end_date.isoformat())
             
        # Sorting
        db_query = db_query.order("date_sso_began", desc=True)
        
        if limit:
            db_query = db_query.limit(limit)
            
        try:
            response = db_query.execute()
            return response.data
        except Exception as e:
            logger.error(f"DB Query failed: {e}")
            return []

    # Helper methods to match SSOClient interface if needed
    # list_permittees, list_counties etc. might still use ArcGIS (fast cached) 
    # OR query DB distinct values.
    # For "Don't break the app", sticking to ArcGIS for metadata (filters) is safer 
    # as DB might be partial initially.
    # But fetching data (slow part) goes to DB.
