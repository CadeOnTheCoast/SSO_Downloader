"""Canonical schema and query helpers for SSO records."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional

from sso_volume import enrich_est_volume_fields, parse_est_volume

# Field names as returned by the ArcGIS layer
UTILITY_ID_FIELD = "permit_no"
UTILITY_NAME_FIELD = "permittee"
COUNTY_FIELD = "county"
START_DATE_FIELD = "date_sso_began"
END_DATE_FIELD = "date_sso_stopped"
VOLUME_GALLONS_FIELD = "volume_gallons"
SSO_ID_FIELD = "sso_id"
RECEIVING_WATER_FIELD = "receiving_water"
CAUSE_FIELD = "cause"
SEWER_SYSTEM_FIELD = "sewer_system"
LOCATION_FIELD = "location"


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
    receiving_water: Optional[str] = None

    x: Optional[float] = None
    y: Optional[float] = None

    raw: Dict[str, Any] = field(default_factory=dict)


def _coerce_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return str(value)
    except Exception:
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    # ArcGIS often returns epoch milliseconds for dates
    if isinstance(value, (int, float)):
        try:
            # Treat values above year 3000 as milliseconds
            if value > 10_000_000_000:
                value = value / 1000.0
            return datetime.fromtimestamp(value)
        except (OSError, OverflowError, ValueError):
            return None
    if isinstance(value, str):
        if value.isdigit():
            return _parse_datetime(float(value))
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def normalize_sso_record(raw: Mapping[str, Any]) -> SSORecord:
    """Convert a raw ArcGIS record to an :class:`SSORecord`.

    The function is defensive: missing keys or parsing errors return ``None``
    for the structured fields without raising exceptions. The original record
    is preserved on ``raw`` for downstream consumers that need additional
    attributes.
    """

    raw_dict = dict(raw)
    enrich_est_volume_fields(raw_dict)

    est_volume_value = _coerce_str(raw_dict.get("est_volume"))
    est_volume_gal, est_volume_is_range, est_volume_range_label = parse_est_volume(
        est_volume_value
    )

    if raw_dict.get("est_volume_gal") is not None:
        try:
            est_volume_gal = int(float(raw_dict.get("est_volume_gal")))
        except (TypeError, ValueError):
            pass

    est_volume_is_range_bool: Optional[bool] = est_volume_is_range
    raw_is_range = raw_dict.get("est_volume_is_range")
    if isinstance(raw_is_range, str):
        est_volume_is_range_bool = raw_is_range.upper() == "Y"
    elif raw_is_range is not None:
        est_volume_is_range_bool = bool(raw_is_range)

    volume_value = _coerce_float(raw_dict.get(VOLUME_GALLONS_FIELD))
    if volume_value is None and est_volume_gal is not None:
        volume_value = _coerce_float(est_volume_gal)

    return SSORecord(
        sso_id=_coerce_str(raw_dict.get(SSO_ID_FIELD)),
        utility_id=_coerce_str(raw_dict.get(UTILITY_ID_FIELD)),
        utility_name=_coerce_str(raw_dict.get(UTILITY_NAME_FIELD) or raw_dict.get("utility_name")),
        sewer_system=_coerce_str(raw_dict.get(SEWER_SYSTEM_FIELD)),
        county=_coerce_str(raw_dict.get(COUNTY_FIELD)),
        location_desc=_coerce_str(raw_dict.get("location_desc") or raw_dict.get(LOCATION_FIELD)),
        date_sso_began=_parse_datetime(raw_dict.get(START_DATE_FIELD)),
        date_sso_stopped=_parse_datetime(raw_dict.get(END_DATE_FIELD)),
        volume_gallons=volume_value,
        est_volume=est_volume_value,
        est_volume_gal=est_volume_gal,
        est_volume_is_range=est_volume_is_range_bool,
        est_volume_range_label=est_volume_range_label,
        cause=_coerce_str(raw_dict.get(CAUSE_FIELD)),
        receiving_water=_coerce_str(
            raw_dict.get(RECEIVING_WATER_FIELD) or raw_dict.get("waterbody")
        ),
        x=_coerce_float(raw_dict.get("x")),
        y=_coerce_float(raw_dict.get("y")),
        raw=raw_dict,
    )


def normalize_sso_records(raw_records: Iterable[Mapping[str, Any]]) -> List[SSORecord]:
    """Normalize a collection of raw records into :class:`SSORecord` objects."""

    return [normalize_sso_record(record) for record in raw_records]


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
