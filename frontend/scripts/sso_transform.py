"""Transformation and normalization logic for SSO records."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, List, Mapping, Optional

from sso_schema import (
    SSORecord,
    CENTRAL_TZ,
    START_DATE_FIELD,
    END_DATE_FIELD,
    VOLUME_GALLONS_FIELD,
    SSO_ID_FIELD,
    UTILITY_ID_FIELD,
    UTILITY_NAME_FIELD,
    SEWER_SYSTEM_FIELD,
    COUNTY_FIELD,
    LOCATION_FIELD,
    CAUSE_FIELD,
    RECEIVING_WATER_FIELD,
    format_datetime_central,
)
from sso_volume import enrich_est_volume_fields, parse_est_volume


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
    """Convert a raw ArcGIS record to an SSORecord."""

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
    """Normalize a collection of raw records into SSORecord objects."""

    return [normalize_sso_record(record) for record in raw_records]


def sso_record_to_csv_row(record: SSORecord) -> Dict[str, Any]:
    """Render an SSORecord to a CSV-friendly mapping."""

    row = dict(record.raw)
    row[START_DATE_FIELD] = format_datetime_central(record.date_sso_began)
    row[END_DATE_FIELD] = format_datetime_central(record.date_sso_stopped)
    return row
