"""FastAPI web layer for SSO downloads and previews."""
from __future__ import annotations

import io
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response
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
from sso_schema import SSOQuery, normalize_sso_records, sso_record_to_csv_row
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


class SSOQueryParams(BaseModel):
    utility_id: Optional[str] = Field(default=None, alias="utility_id")
    utility_name: Optional[str] = Field(default=None, alias="utility_name")
    permit: Optional[str] = Field(default=None, alias="permit")
    county: Optional[str] = None
    start_date: Optional[str] = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
    )
    end_date: Optional[str] = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
    )
    limit: Optional[int] = Field(default=None, ge=1, le=50000)

    @validator("utility_id", "utility_name", "permit", "county", pre=True)
    def _handle_undefined(cls, value):
        if value in ("undefined", "null", ""):
            return None
        return value

    @field_validator("start_date", "end_date")
    def _validate_date(cls, value: Optional[str]):
        if value is None:
            return value
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:  # pragma: no cover - handled by pydantic already
            raise ValueError("Dates must use YYYY-MM-DD format") from exc
        return value

    def _parse_date(self, value: Optional[str]):
        if value is None:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    def has_filters(self) -> bool:
        return any(
            [
                self.permit,
                self.utility_id,
                self.utility_name,
                self.county,
                self.start_date,
                self.end_date,
            ]
        )

    def to_sso_query(
        self, permit_map: Optional[dict[str, dict[str, object]]] = None
    ) -> SSOQuery:
        county = self.county.title() if self.county else None
        utility_id = self.permit or self.utility_id

        permit_ids: Optional[list[str]] = None
        def _permits_from_map(value: str) -> Optional[list[str]]:
            if not permit_map or not value:
                return None
            entry = permit_map.get(value.lower())
            if entry and entry.get("permits"):
                return list(entry["permits"])
            for details in permit_map.values():
                permits = details.get("permits") or []
                if value in permits:
                    return list(permits)
            return None

        if utility_id:
            permit_ids = _permits_from_map(utility_id) or [utility_id]
        elif permit_map and self.utility_name:
            permits = _permits_from_map(self.utility_name)
            if permits:
                permit_ids = permits

        return SSOQuery(
            utility_id=None if permit_ids else self.utility_id,
            utility_name=None if permit_ids else self.utility_name,
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



def _load_options(client: SSOClient) -> dict[str, object]:
    utilities: list[dict[str, object]] = []
    permittees: list[dict[str, object]] = []
    counties = list(DEFAULT_COUNTIES)

    try:
        fresh_permittees = client.list_permittees()
        if fresh_permittees:
            permittees = fresh_permittees
            utilities = [
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "permits": item.get("permits", []),
                }
                for item in fresh_permittees
            ]
    except Exception:
        utilities = DEFAULT_UTILITIES
        permittees = [
            {"id": item["id"], "name": item["name"], "permits": [item["id"]]}
            for item in DEFAULT_UTILITIES
        ]

    try:
        fresh_counties = client.list_counties()
        if fresh_counties:
            counties = fresh_counties
    except Exception:
        counties = list(DEFAULT_COUNTIES)

    return {"utilities": utilities, "permittees": permittees, "counties": counties}


@app.get("/filters")
def list_filters(client: SSOClient = Depends(get_client)) -> dict[str, object]:
    return _load_options(client)


@app.get("/api/options")
def list_options(client: SSOClient = Depends(get_client)) -> dict[str, object]:
    """Alias for UI filter metadata used by the dashboard."""

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
    _ensure_filters(params)
    query = _to_query(params, client)
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        safe_limit = params.bounded_limit(
            default=MAX_WEB_RECORDS, maximum=MAX_WEB_RECORDS
        )
        records = client.fetch_ssos(query=query, limit=safe_limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for record in records:
        enrich_est_volume_fields(record)

    normalized_records = normalize_sso_records(records)
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
    query = _to_query(params, client)
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        safe_limit = params.bounded_limit(
            default=MAX_WEB_RECORDS, maximum=MAX_WEB_RECORDS
        )
        raw_records = client.fetch_ssos(query=query, limit=safe_limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for record in raw_records:
        enrich_est_volume_fields(record)

    records_norm = normalize_sso_records(raw_records)
    summary = build_dashboard_summary(
        records_norm,
        date_range={"min": params.start_date, "max": params.end_date},
    )

    if params.permit or params.utility_id or params.utility_name:
        summary["top_utilities_pie"] = []

    return summary


@app.get("/api/ssos/summary")
def dashboard_summary(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    return _build_dashboard_payload(params, client)


@app.get("/summary")
def summary(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    """Legacy summary endpoint kept for backward compatibility."""
    return _build_dashboard_payload(params, client)


@app.get("/series/by_date")
def series_by_date(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    query = _to_query(params, client)
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        raw_records = client.fetch_ssos(query=query, limit=params.limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    records_norm = normalize_sso_records(raw_records)
    series = time_series_by_date(records_norm)

    return {"points": [asdict(point) for point in series]}


@app.get("/series/by_utility")
def series_by_utility(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    query = _to_query(params, client)
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        raw_records = client.fetch_ssos(query=query, limit=params.limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    records_norm = normalize_sso_records(raw_records)
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
    offset: int = Field(default=0, ge=0)
    limit: Optional[int] = Field(default=200, ge=1, le=MAX_WEB_RECORDS)


def _fetch_normalized_records(
    params: RecordsQueryParams,
    client: SSOClient,
    *,
    default_limit: int = 200,
    maximum: int = MAX_WEB_RECORDS,
):
    """Shared record fetching logic for JSON table endpoints."""

    query = _to_query(params, client)
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_limit = params.bounded_limit(default=params.limit or default_limit, maximum=maximum)

    try:
        raw_records = client.fetch_ssos(query=query, limit=safe_limit + params.offset)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    for record in raw_records:
        enrich_est_volume_fields(record)

    normalized = normalize_sso_records(raw_records)
    sliced = normalized[params.offset : params.offset + safe_limit]
    return sliced, len(normalized), safe_limit


def _serialize_record(record) -> dict[str, object]:
    return {
        "id": record.sso_id,
        "utility_id": record.utility_id,
        "utility_name": record.utility_name,
        "county": record.county,
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
        "x": record.x,
        "y": record.y,
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
