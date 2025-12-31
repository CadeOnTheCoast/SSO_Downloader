"""Canonical schema and query helpers for SSO records."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

# Field names as returned by the ArcGIS layer
UTILITY_ID_FIELD = "permit_no"
UTILITY_NAME_FIELD = "permittee"
COUNTY_FIELD = "county"
START_DATE_FIELD = "date_sso_began"
END_DATE_FIELD = "date_sso_stopped"
VOLUME_GALLONS_FIELD = "volume_gallons"
SSO_ID_FIELD = "sso_id"
CAUSE_FIELD = "cause"
CAUSE_CATEGORY_FIELD = "cause_category"
SEWER_SYSTEM_FIELD = "sewer_system"
LOCATION_FIELD = "location"
RECEIVING_WATER_FIELD = "receiving_water"


CENTRAL_TZ = ZoneInfo("America/Chicago")


@dataclass
class SSORecord:
    """Canonical representation of an SSO record."""

    sso_id: Optional[str] = None
    utility_id: Optional[str] = None
    utility_name: Optional[str] = None
    sewer_system: Optional[str] = None
    county: Optional[str] = None
    location_desc: Optional[str] = None

    date_sso_began: Optional[datetime] = None
    date_sso_stopped: Optional[datetime] = None

    volume_gallons: Optional[float] = None
    est_volume: Optional[str] = None
    est_volume_gal: Optional[int] = None
    est_volume_is_range: Optional[bool] = None
    est_volume_range_label: Optional[str] = None
    cause: Optional[str] = None
    cause_category: Optional[str] = None
    receiving_water: Optional[str] = None

    x: Optional[float] = None
    y: Optional[float] = None

    raw: Dict[str, Any] = field(default_factory=dict)


def format_datetime_central(value: Optional[datetime]) -> Optional[str]:
    """Format datetimes in America/Chicago for CSV/JSON output."""

    if value is None:
        return None

    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        localized = dt.astimezone(CENTRAL_TZ)
    except Exception:
        return None

    return localized.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class SSOQuery:
    """Filter model for querying the SSO ArcGIS layer."""

    utility_id: Optional[str] = None
    utility_name: Optional[str] = None
    permit_ids: Optional[List[str]] = None
    county: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_volume_gallons: Optional[float] = None
    max_volume_gallons: Optional[float] = None
    extra_params: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        if self.min_volume_gallons is not None and self.min_volume_gallons < 0:
            raise ValueError("min_volume_gallons cannot be negative")
        if self.max_volume_gallons is not None and self.max_volume_gallons < 0:
            raise ValueError("max_volume_gallons cannot be negative")
        if (
            self.min_volume_gallons is not None
            and self.max_volume_gallons is not None
            and self.min_volume_gallons > self.max_volume_gallons
        ):
            raise ValueError("min_volume_gallons cannot exceed max_volume_gallons")

    def _quote(self, value: str) -> str:
        return value.replace("'", "''")

    def build_where_clause(self) -> str:
        self.validate()
        clauses: List[str] = ["1=1"]

        if self.start_date and self.end_date:
            end_limit = self.end_date + timedelta(days=1)
            clauses.append(
                f"{START_DATE_FIELD} >= DATE '{self.start_date} 00:00:00' "
                f"AND {START_DATE_FIELD} < DATE '{end_limit} 00:00:00'"
            )
        elif self.start_date:
            clauses.append(f"{START_DATE_FIELD} >= DATE '{self.start_date} 00:00:00'")
        elif self.end_date:
            end_limit = self.end_date + timedelta(days=1)
            clauses.append(f"{START_DATE_FIELD} < DATE '{end_limit} 00:00:00'")

        if self.county:
            clauses.append(f"{COUNTY_FIELD} = '{self._quote(self.county)}'")
        if self.permit_ids:
            permit_values = ",".join(
                f"'{self._quote(permit)}'" for permit in self.permit_ids if permit
            )
            if permit_values:
                clauses.append(f"{UTILITY_ID_FIELD} IN ({permit_values})")
        elif self.utility_id:
            clauses.append(f"{UTILITY_ID_FIELD} = '{self._quote(self.utility_id)}'")
        if self.utility_name:
            clauses.append(f"{UTILITY_NAME_FIELD} = '{self._quote(self.utility_name)}'")
        if self.min_volume_gallons is not None:
            clauses.append(f"{VOLUME_GALLONS_FIELD} >= {self.min_volume_gallons}")
        if self.max_volume_gallons is not None:
            clauses.append(f"{VOLUME_GALLONS_FIELD} <= {self.max_volume_gallons}")

        return " AND ".join(clauses)

    def to_query_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "where": self.build_where_clause(),
            "orderByFields": START_DATE_FIELD,
        }
        if self.extra_params:
            params.update(self.extra_params)
        return params
