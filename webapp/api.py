"""FastAPI web layer for SSO downloads and previews."""
from __future__ import annotations

import io
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator

from sso_analytics import summarize_overall_volume, top_utilities_by_volume
from sso_client import SSOClient, SSOClientError
from sso_export import write_ssos_to_csv_filelike
from sso_schema import SSOQuery, normalize_sso_records

app = FastAPI(title="SSO Downloader")

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

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
    return templates.TemplateResponse("index.html", {"request": request})


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


@app.get("/summary")
def summary(
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
        raw_records = client.fetch_ssos(query=query, limit=params.limit)
    except SSOClientError as exc:  # pragma: no cover - network errors are mocked in tests
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    records_norm = normalize_sso_records(raw_records)
    overall = summarize_overall_volume(records_norm)
    top_util = top_utilities_by_volume(records_norm, n=5)

    return {
        "overall": asdict(overall),
        "top_utilities": [asdict(item) for item in top_util],
    }
