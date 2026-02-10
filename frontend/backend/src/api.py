"""FastAPI web layer for SSO downloads and previews."""
from __future__ import annotations

import io
import sys
import json
import time
from functools import lru_cache
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator, validator

from sso_analytics import (
    build_dashboard_summary,
    summarize_overall_volume,
    summarize_volume_by_utility,
    top_utilities_by_volume,
    time_series_by_date,
)
from sso_client import SSOClient, SSOClientError
from sso_export import write_ssos_to_csv_filelike
from sso_schema import SSOQuery
from sso_transform import normalize_sso_records, sso_record_to_csv_row
from sso_volume import enrich_est_volume_fields
from options_data import ALABAMA_COUNTIES

app = FastAPI(title="SSO Downloader")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "traceback": traceback.format_exc(),
            "type": type(exc).__name__
        }
    )

MAX_WEB_RECORDS = 20000

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# TODO: Load from configuration or persisted metadata
DEFAULT_UTILITIES = [
    {"id": "AL0046744", "name": "Prichard Water Works"},
    {"id": "AL0027561", "name": "Mobile Area Water & Sewer"},
    {"id": "AL0063002", "name": "City of Fairhope"},
]
DEFAULT_COUNTIES = ALABAMA_COUNTIES


def _safe_permit_map(client: SSOClient) -> dict[str, dict[str, object]]:
    try:
        return client.permittee_permit_map()
    except Exception:
        return {}


class SSOQueryParams:
    def __init__(
        self,
        utility_id: Optional[str] = Query(None),
        utility_ids: Optional[list[str]] = Query(None),
        utility_name: Optional[str] = Query(None),
        permit: Optional[str] = Query(None),
        permits: Optional[list[str]] = Query(None),
        county: Optional[str] = Query(None),
        start_date: Optional[str] = Query(
            None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
        ),
        end_date: Optional[str] = Query(
            None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
        ),
        limit: Optional[int] = Query(None, ge=1, le=50000),
    ):
        self.utility_id = utility_id
        self.utility_ids = utility_ids
        self.utility_name = utility_name
        self.permit = permit
        self.permits = permits
        self.county = county
        self.start_date = start_date
        self.end_date = end_date
        self.limit = limit

    def _parse_date(self, value: Optional[str]):
        if value is None:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    def has_filters(self) -> bool:
        return any(
            [
                self.permit,
                self.permits,
                self.utility_id,
                self.utility_ids,
                self.utility_name,
                self.county,
                self.start_date,
                self.end_date,
            ]
        )

    def to_sso_query(
        self, permit_map: Optional[dict[str, dict[str, object]]] = None
    ) -> SSOQuery:
        # Backend doesn't support county filtering reliably, so we filter in Python
        county = None 
        
        # Collect all permit IDs from all utility sources
        all_permits: set[str] = set()
        
        def _resolve_permits(value: str):
            if not permit_map or not value:
                return [value] if value else []
            entry = permit_map.get(value.lower())
            if entry and entry.get("permits"):
                return list(entry["permits"])
            for details in permit_map.values():
                p_list = details.get("permits") or []
                if value in p_list:
                    return list(p_list)
            return [value]

        # 1. Check for explicit permit filters first
        if self.permit:
            all_permits.add(self.permit)
        if self.permits:
            for pid in self.permits:
                all_permits.add(pid)
        
        # 2. If NO explicit permits, fall back to utility-wide permits
        if not all_permits:
            if self.utility_id:
                all_permits.update(_resolve_permits(self.utility_id))
            if self.utility_ids:
                for uid in self.utility_ids:
                    all_permits.update(_resolve_permits(uid))
            if self.utility_name:
                all_permits.update(_resolve_permits(self.utility_name))

        permit_ids = sorted(list(all_permits)) if all_permits else None

        return SSOQuery(
            county=county,
            permit_ids=permit_ids,
            start_date=self._parse_date(self.start_date),
            end_date=self._parse_date(self.end_date),
        )

    def bounded_limit(self, *, default: int, maximum: int) -> int:
        """Return a safe limit based on provided value and bounds."""

        if self.limit is None:
            return min(default, maximum)
        return min(self.limit, maximum)


def get_client() -> SSOClient:
    return SSOClient()


def create_app() -> FastAPI:
    return app


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}




_OPTIONS_CACHE = None
_OPTIONS_CACHE_TIME = 0
OPTIONS_CACHE_TTL = 360  # 6 minutes

def _load_options(client: SSOClient) -> dict[str, object]:
    global _OPTIONS_CACHE, _OPTIONS_CACHE_TIME
    now = time.time()
    if _OPTIONS_CACHE and (now - _OPTIONS_CACHE_TIME < OPTIONS_CACHE_TTL):
        return _OPTIONS_CACHE

    utilities: list[dict[str, object]] = []
    permittees: list[dict[str, object]] = []
    counties = ALABAMA_COUNTIES

    try:
        fresh_permittees = client.list_permittees()
        if fresh_permittees:
            permittees = fresh_permittees
            
            # Prichard Patch: Ensure AL0046744 is included in Utilities of Prichard (AL0023205)
            # and remove AL0046744 if it exists as a separate entry to avoid confusion/duplication
            prichard_id = "AL0023205"
            missing_permit = "AL0046744"
            
            patched_utilities = []
            for item in fresh_permittees:
                # Skip the standalone "missing permit" entry if it exists separately
                if item.get("id") == missing_permit:
                    continue
                    
                u_obj = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "slug": item.get("slug"),
                    "permits": list(item.get("permits", [])), # Safe copy
                    "aliases": list(item.get("aliases", [])), # Safe copy
                }
                
                # Patch Prichard
                if item.get("id") == prichard_id:
                    current_permits = u_obj["permits"]
                    if missing_permit not in current_permits:
                        # Add it
                        u_obj["permits"].append(missing_permit)
                        # Ensure uniqueness just in case
                        u_obj["permits"] = sorted(list(set(u_obj["permits"])))
                        
                patched_utilities.append(u_obj)
            
            utilities = patched_utilities
    except Exception:
        utilities = DEFAULT_UTILITIES
        permittees = [
            {"id": item["id"], "name": item["name"], "permits": [item["id"]]}
            for item in DEFAULT_UTILITIES
        ]


    res = {"utilities": utilities, "permittees": permittees, "counties": counties}
    _OPTIONS_CACHE = res
    _OPTIONS_CACHE_TIME = now
    return res


@app.get("/filters")
def list_filters(response: Response, client: SSOClient = Depends(get_client)) -> dict[str, object]:
    # Cache filters for 24 hours (s-maxage) on CDN, 1 hour (max-age) on client
    # stale-while-revalidate allows serving old content while updating in background
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=600"
    return _load_options(client)


@app.get("/api/options")
def list_options(response: Response, client: SSOClient = Depends(get_client)) -> dict[str, object]:
    """Alias for UI filter metadata used by the dashboard."""
    response.headers["Cache-Control"] = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=600"
    return _load_options(client)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


def _ensure_filters(params: SSOQueryParams) -> None:
    if not params.has_filters():
        raise HTTPException(
            status_code=400,
            detail="At least one filter (utility, county, or date range) is required.",
        )


def _to_query(params: SSOQueryParams, client: SSOClient) -> SSOQuery:
    permit_map = _safe_permit_map(client)
    return params.to_sso_query(permit_map)


def _build_filename(params: SSOQueryParams) -> str:
    parts = ["ssos"]
    if params.permit:
        parts.append(params.permit)
    elif params.utility_id:
        parts.append(params.utility_id)
    elif params.utility_name:
        parts.append(params.utility_name.replace(" ", "_"))
    elif params.county:
        parts.append(params.county.replace(" ", "_"))
    else:
        parts.append("all")

    if params.start_date:
        parts.append(params.start_date)
    if params.end_date:
        parts.append(params.end_date)
    return "_".join(parts) + ".csv"


def _download_csv_response(
    params: SSOQueryParams, client: SSOClient
) -> StreamingResponse:
    normalized_records = _fetch_all_filtered_records(params, client, default_limit=MAX_WEB_RECORDS)
    csv_rows = [sso_record_to_csv_row(record) for record in normalized_records]

    buffer = io.StringIO()
    write_ssos_to_csv_filelike(csv_rows, buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="{_build_filename(params)}"'
    }
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


@app.get("/download")
def download_csv(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    return _download_csv_response(params, client)


def _build_dashboard_payload(params: SSOQueryParams, client: SSOClient) -> dict:
    records_norm = _fetch_all_filtered_records(params, client, default_limit=MAX_WEB_RECORDS)
    summary = build_dashboard_summary(
        records_norm,
        date_range={"min": params.start_date, "max": params.end_date},
    )

    if params.permit or params.utility_id or params.utility_name:
        summary["top_utilities_pie"] = []

    return summary


@app.get("/api/ssos/summary")
def dashboard_summary(
    response: Response,
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    # Cache summary for 5 minutes (300s) on CDN
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    return _build_dashboard_payload(params, client)


@app.get("/summary")
def summary(
    response: Response,
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    """Legacy summary endpoint kept for backward compatibility."""
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    return _build_dashboard_payload(params, client)


@app.get("/series/by_date")
def series_by_date(
    response: Response,
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    records_norm = _fetch_all_filtered_records(
        params, client, default_limit=params.limit or MAX_WEB_RECORDS
    )
    series = time_series_by_date(records_norm)

    return {"points": series}


@app.get("/series/by_utility")
def series_by_utility(
    response: Response,
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=60"
    records_norm = _fetch_all_filtered_records(
        params, client, default_limit=params.limit or MAX_WEB_RECORDS
    )
    grouped = summarize_volume_by_utility(records_norm)
    counts: dict[str, int] = {}
    for record in records_norm:
        if record.utility_name:
            counts[record.utility_name] = counts.get(record.utility_name, 0) + 1

    bars = [
        {
            "label": item.group_key,
            "count": counts.get(item.group_key, item.count),
            "total_volume_gallons": item.total_volume_gallons,
        }
        for item in grouped
    ]
    return {"bars": bars}


class RecordsQueryParams(SSOQueryParams):
    def __init__(
        self,
        utility_id: Optional[str] = Query(None),
        utility_ids: Optional[list[str]] = Query(None),
        utility_name: Optional[str] = Query(None),
        permit: Optional[str] = Query(None),
        permits: Optional[list[str]] = Query(None),
        county: Optional[str] = Query(None),
        start_date: Optional[str] = Query(
            None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
        ),
        end_date: Optional[str] = Query(
            None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
        ),
        limit: Optional[int] = Query(200, ge=1, le=MAX_WEB_RECORDS),
        offset: int = Query(0, ge=0),
        sort_by: Optional[str] = Query(None),
        sort_order: Optional[str] = Query("desc"),
    ):
        super().__init__(
            utility_id=utility_id,
            utility_ids=utility_ids,
            utility_name=utility_name,
            permit=permit,
            permits=permits,
            county=county,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        self.offset = offset
        self.sort_by = sort_by
        self.sort_order = sort_order


def _fetch_normalized_records(
    params: RecordsQueryParams,
    client: SSOClient,
    *,
    default_limit: int = 200,
    maximum: int = MAX_WEB_RECORDS,
):
    """Shared record fetching logic for JSON table endpoints."""

    query = _to_query(params, client)
    
    db_sort_map = {
        "date_sso_began": "date_sso_began",
        "utility_name": "permittee",
        "county": "county",
        "receiving_water": "rec_stream",
    }
    
    db_sort_field = db_sort_map.get(params.sort_by)
    safe_limit = params.bounded_limit(default=params.limit or default_limit, maximum=maximum)

    # Check if we need to filter by county in Python
    python_county_filter = params.county

    # If sorting by DB field AND no python filtering needed, efficient fetch
    if db_sort_field and not python_county_filter:
        direction = "DESC" if params.sort_order == "desc" else "ASC"
        query.extra_params = query.extra_params or {}
        query.extra_params["orderByFields"] = f"{db_sort_field} {direction}"
        fetch_limit = safe_limit + params.offset
    else:
        # If sorting by Volume (computed) or County Filter, fetch everything (capped)
        fetch_limit = maximum

    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        raw_records = client.fetch_ssos(query=query, limit=fetch_limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for record in raw_records:
        enrich_est_volume_fields(record)

    normalized = normalize_sso_records(raw_records)
    
    # Enrich with County if needed for Filtering or Sorting
    # (Serializer will enrich displayed records JIT, but we need it earlier here)
    if python_county_filter or params.sort_by == "county":
        for r in normalized:
            if not r.county and r.x and r.y:
                r.county = get_county(r.y, r.x)

    # Apply Python County Filter
    if python_county_filter:
         target = python_county_filter.lower().replace(" county", "").strip()
         normalized = [
             r for r in normalized 
             if r.county and r.county.lower().replace(" county", "").strip() == target
         ]
    
    # Python Sort for non-DB fields (Volume or County)
    if not db_sort_field:
         if params.sort_by == "volume_gallons":
             normalized.sort(
                 key=lambda r: r.volume_gallons or 0, 
                 reverse=(params.sort_order == "desc")
             )
         elif params.sort_by == "county":
             normalized.sort(
                 key=lambda r: r.county or "", 
                 reverse=(params.sort_order == "desc")
             )
         
    sliced = normalized[params.offset : params.offset + safe_limit]
    return sliced, len(normalized), safe_limit


AL_COUNTY_FEATURES = None


def _load_counties():
    global AL_COUNTY_FEATURES
    if AL_COUNTY_FEATURES is not None:
        return

    # Try paths relative to CWD (root) and this file
    # Common deployment paths:
    # 1. Root relative: frontend/data/al_counties.json
    # 2. File relative: ../../../data/al_counties.json
    
    paths = [
        Path("frontend/data/al_counties.json"),
        Path(__file__).resolve().parents[2] / "data" / "al_counties.json"
    ]
    
    for p in paths:
        if p.exists():
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                    AL_COUNTY_FEATURES = data["features"]
                    # print(f"Loaded {len(AL_COUNTY_FEATURES)} counties from {p}")
                    return
            except Exception as e:
                print(f"Error loading counties from {p}: {e}")
                
    print("Warning: Could not find al_counties.json")
    AL_COUNTY_FEATURES = []


def point_in_polygon(x, y, poly) -> bool:
    """Ray casting algorithm for Point in Polygon."""
    n = len(poly)
    inside = False
    p1x, p1y = poly[0]
    for i in range(1, n + 1):
        p2x, p2y = poly[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside


@lru_cache(maxsize=4096)
def get_county(lat: Optional[float], lon: Optional[float]) -> Optional[str]:
    _load_counties()
    if not AL_COUNTY_FEATURES or lat is None or lon is None:
        return None

    # Brute force 67 counties is fast enough (<10ms)
    for feature in AL_COUNTY_FEATURES:
        geom = feature["geometry"]
        coords = geom["coordinates"]
        
        match = False
        if geom["type"] == "Polygon":
            if point_in_polygon(lon, lat, coords[0]):
                match = True
        elif geom["type"] == "MultiPolygon":
            for poly in coords:
                if point_in_polygon(lon, lat, poly[0]):
                    match = True
                    break
        
        if match:
            return feature["properties"].get("NAME") 
    return None


@lru_cache(maxsize=128)
def _cached_query_results(
    start_date: Optional[str],
    end_date: Optional[str],
    utility_id: Optional[str],
    utility_ids_json: Optional[str],
    utility_name: Optional[str],
    county: Optional[str],
    limit: Optional[int],
    permit: Optional[str],
    permits_json: Optional[str],
):
    """
    Internal helper to cache the results of a filtered ArcGIS query.
    We pass a dummy client parameters to ensure uniqueness if needed, but 
    usually the singleton behavior is fine.
    """
    # Create a fresh client and params for the actual fetch
    client = SSOClient()
    
    # We need to reconstruct SSOQueryParams or similar logic
    # Actually, it's easier to just move the logic here or pass the query object if it was hashable.
    # Since it's not, we'll just reconstruct a minimal SSOQueryParams to use its to_sso_query logic.
    
    utility_ids = json.loads(utility_ids_json) if utility_ids_json else None
    permits = json.loads(permits_json) if permits_json else None
    
    params = SSOQueryParams(
        utility_id=utility_id,
        utility_ids=utility_ids,
        utility_name=utility_name,
        permit=permit,
        permits=permits,
        county=county,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    # This logic matches _fetch_all_filtered_records but it's the one we cache
    query = _to_query(params, client)
    
    # If filtering by county, we must fetch max records to filter in memory
    python_county_filter = params.county
    fetch_limit = MAX_WEB_RECORDS if python_county_filter else (params.limit or MAX_WEB_RECORDS)
    
    try:
        query.validate()
        raw_records = client.fetch_ssos(query=query, limit=fetch_limit)
    except Exception as exc:
        # Don't cache failures
        raise exc

    for r in raw_records:
        enrich_est_volume_fields(r)

    normalized = normalize_sso_records(raw_records)
    
    # Enrich
    for r in normalized:
        if not r.county and r.x and r.y:
            r.county = get_county(r.y, r.x)
            
    # Filter
    if python_county_filter:
         target = python_county_filter.lower().replace(" county", "").strip()
         normalized = [
             r for r in normalized 
             if r.county and r.county.lower().replace(" county", "").strip() == target
         ]
         
    return normalized


def _fetch_all_filtered_records(
    params: SSOQueryParams, client: SSOClient, default_limit: int = MAX_WEB_RECORDS
):
    """Fetch, normalize, enrich (county), and filter records."""
    # Convert list params to JSON strings for hashability in lru_cache
    utility_ids_json = json.dumps(params.utility_ids) if params.utility_ids else None
    permits_json = json.dumps(params.permits) if params.permits else None
    
    return _cached_query_results(
        params.start_date,
        params.end_date,
        params.utility_id,
        utility_ids_json,
        params.utility_name,
        params.county,
        params.limit,
        params.permit,
        permits_json
    )


def _serialize_record(record) -> dict[str, object]:
    # Determine county if missing
    county = record.county
    if not county and record.y and record.x:
        county = get_county(record.y, record.x)

    return {
        "id": record.sso_id,
        "utility_id": record.utility_id,
        "utility_name": record.utility_name,
        "county": county,
        "date_sso_began": record.date_sso_began.isoformat()
        if record.date_sso_began
        else None,
        "date_sso_stopped": record.date_sso_stopped.isoformat()
        if record.date_sso_stopped
        else None,
        "volume_gallons": record.volume_gallons,
        "cause": record.cause,
        "receiving_water": record.receiving_water,
        "address": record.location_desc,
        "latitude": record.y,
        "longitude": record.x,
    }


@app.get("/records")
def list_records(
    params: RecordsQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    sliced, total, safe_limit = _fetch_normalized_records(
        params, client, default_limit=500, maximum=MAX_WEB_RECORDS
    )

    return {
        "records": [_serialize_record(record) for record in sliced],
        "total": total,
        "offset": params.offset,
        "limit": safe_limit,
    }


@app.get("/api/ssos")
def api_ssos(
    params: RecordsQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    sliced, total, safe_limit = _fetch_normalized_records(
        params, client, default_limit=200, maximum=MAX_WEB_RECORDS
    )

    return {
        "items": [_serialize_record(record) for record in sliced],
        "total": total,
        "offset": params.offset,
        "limit": safe_limit,
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})


@app.get("/api/ssos.csv")
def api_ssos_csv(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    return _download_csv_response(params, client)
