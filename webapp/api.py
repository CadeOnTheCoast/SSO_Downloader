"""FastAPI web layer for SSO downloads and previews."""
from __future__ import annotations

import io
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from sso_analytics import (
    build_dashboard_summary,
    summarize_overall_volume,
    summarize_volume_by_utility,
    top_utilities_by_volume,
    time_series_by_date,
)
from sso_client import SSOClient, SSOClientError
from sso_export import write_ssos_to_csv_filelike
from sso_schema import SSOQuery, normalize_sso_records

app = FastAPI(title="SSO Downloader")

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
DEFAULT_COUNTIES = [
    "Mobile",
    "Baldwin",
    "Montgomery",
    "Jefferson",
]


class SSOQueryParams(BaseModel):
    utility_id: Optional[str] = Field(default=None, alias="utility_id")
    utility_name: Optional[str] = Field(default=None, alias="utility_name")
    county: Optional[str] = None
    start_date: Optional[str] = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
    )
    end_date: Optional[str] = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"
    )
    limit: Optional[int] = Field(default=None, ge=1, le=50000)

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
                self.utility_id,
                self.utility_name,
                self.county,
                self.start_date,
                self.end_date,
            ]
        )

    def to_sso_query(self) -> SSOQuery:
        return SSOQuery(
            utility_id=self.utility_id,
            utility_name=self.utility_name,
            county=self.county,
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


@app.get("/filters")
def list_filters() -> dict[str, object]:
    return {"utilities": DEFAULT_UTILITIES, "counties": DEFAULT_COUNTIES}


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})


def _ensure_filters(params: SSOQueryParams) -> None:
    if not params.has_filters():
        raise HTTPException(
            status_code=400,
            detail="At least one filter (utility, county, or date range) is required.",
        )


def _build_filename(params: SSOQueryParams) -> str:
    parts = ["ssos"]
    if params.utility_id:
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


@app.get("/download")
def download_csv(
    params: SSOQueryParams = Depends(),
    client: SSOClient = Depends(get_client),
):
    _ensure_filters(params)
    query = params.to_sso_query()
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        records = client.fetch_ssos(query=query, limit=params.limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    buffer = io.StringIO()
    write_ssos_to_csv_filelike(records, buffer)
    buffer.seek(0)

    headers = {
        "Content-Disposition": f'attachment; filename="{_build_filename(params)}"'
    }
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )


def _build_dashboard_payload(params: SSOQueryParams, client: SSOClient) -> dict:
    _ensure_filters(params)
    query = params.to_sso_query()
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_limit = params.bounded_limit(default=5000, maximum=20000)

    try:
        raw_records = client.fetch_ssos(query=query, limit=safe_limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    records_norm = normalize_sso_records(raw_records)
    return build_dashboard_summary(records_norm)


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
    _ensure_filters(params)
    query = params.to_sso_query()
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_limit = params.bounded_limit(default=5000, maximum=10000)

    try:
        raw_records = client.fetch_ssos(query=query, limit=safe_limit)
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
    _ensure_filters(params)
    query = params.to_sso_query()
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_limit = params.bounded_limit(default=5000, maximum=10000)

    try:
        raw_records = client.fetch_ssos(query=query, limit=safe_limit)
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
    limit: Optional[int] = Field(default=200, ge=1, le=10000)


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
    _ensure_filters(params)
    query = params.to_sso_query()
    try:
        query.validate()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    safe_limit = params.bounded_limit(default=500, maximum=1000)

    try:
        raw_records = client.fetch_ssos(query=query, limit=safe_limit + params.offset)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    normalized = normalize_sso_records(raw_records)
    sliced = normalized[params.offset : params.offset + safe_limit]

    return {
        "records": [_serialize_record(record) for record in sliced],
        "total": len(normalized),
        "offset": params.offset,
        "limit": safe_limit,
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"request": request})
