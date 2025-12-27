"""Analytics and QA helpers for SSO records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence
from typing import Literal

from sso_schema import SSORecord


@dataclass
class VolumeSummary:
    count: int
    total_volume_gallons: float
    mean_volume_gallons: Optional[float]
    median_volume_gallons: Optional[float]
    max_volume_gallons: Optional[float]


@dataclass
class GroupVolumeSummary(VolumeSummary):
    group_key: str


@dataclass
class SpillRecordSummary:
    sso_id: Optional[str]
    utility_name: Optional[str]
    county: Optional[str]
    date_sso_began: Optional[datetime]
    volume_gallons: Optional[float]
    description: Optional[str]


@dataclass
class DateSeriesPoint:
    date: str
    count: int
    total_volume_gallons: float


IssueSeverity = Literal["info", "warning", "error"]

# Volume buckets are inclusive of the lower bound and exclusive of the upper
# bound (except when the upper bound is ``None`` which means "and up").
VOLUME_BUCKETS: List[tuple[float, Optional[float]]] = [
    (0, 1000),
    (1000, 10_000),
    (10_000, 50_000),
    (50_000, 100_000),
    (100_000, None),
]

RECEIVING_WATER_KEYWORDS = (
    "river",
    "creek",
    "bay",
    "branch",
    "lake",
    "pond",
    "gully",
    "lagoon",
    "swamp",
    "stream",
    "ditch",
    "canal",
    "cove",
    "slough",
    "harbor",
)

CONTAINED_LABEL = "Contained / did not reach state waters"
CONTAINED_PHRASES = {
    "ground absorbed",
    "backup into building",
    "backup into building/residence",
    "contained",
    "did not reach us waters",
    "did not reach waters",
}


@dataclass
class QAIssue:
    severity: IssueSeverity
    code: str
    message: str
    sso_id: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None


def _usable_volume(record: SSORecord) -> Optional[float]:
    if record.volume_gallons is None:
        return None
    if record.volume_gallons < 0:
        return None
    return record.volume_gallons


def _normalize_receiving_water_name(raw_value: Optional[str]) -> Optional[str]:
    if not raw_value:
        return None
    value = str(raw_value).strip()
    if not value:
        return None

    parts = [part.strip() for part in value.split(";") if part and part.strip()]
    if not parts:
        parts = [value]

    for part in parts:
        lower_part = part.lower()
        if any(keyword in lower_part for keyword in RECEIVING_WATER_KEYWORDS):
            return part

    lower_value = value.lower()
    if any(phrase in lower_value for phrase in CONTAINED_PHRASES):
        return CONTAINED_LABEL

    return parts[0] if parts else value


def _best_volume(record: SSORecord) -> Optional[float]:
    est_high = getattr(record, "est_volume_high", None)
    if est_high is None and hasattr(record, "raw"):
        est_high = record.raw.get("est_volume_high")
    if est_high is not None:
        try:
            return float(est_high)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            pass
    if record.est_volume_gal is not None:
        try:
            return float(record.est_volume_gal)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return None
    return _usable_volume(record)


def _volume_stats(volumes: List[float]) -> VolumeSummary:
    count = len(volumes)
    if not volumes:
        return VolumeSummary(0, 0.0, None, None, None)
    total = float(sum(volumes))
    return VolumeSummary(
        count=count,
        total_volume_gallons=total,
        mean_volume_gallons=mean(volumes),
        median_volume_gallons=median(volumes),
        max_volume_gallons=max(volumes),
    )


def summarize_overall_volume(records: Iterable[SSORecord]) -> VolumeSummary:
    volumes = [vol for record in records if (vol := _usable_volume(record)) is not None]
    return _volume_stats(volumes)


def _summaries_from_groups(groups: Dict[str, List[float]]) -> List[GroupVolumeSummary]:
    summaries: List[GroupVolumeSummary] = []
    for key, volumes in groups.items():
        base = _volume_stats(volumes)
        summaries.append(
            GroupVolumeSummary(
                group_key=key,
                count=base.count,
                total_volume_gallons=base.total_volume_gallons,
                mean_volume_gallons=base.mean_volume_gallons,
                median_volume_gallons=base.median_volume_gallons,
                max_volume_gallons=base.max_volume_gallons,
            )
        )
    summaries.sort(
        key=lambda item: (
            -item.total_volume_gallons,
            item.group_key.lower(),
        )
    )
    return summaries


def summarize_volume_by_utility(records: Iterable[SSORecord]) -> List[GroupVolumeSummary]:
    groups: Dict[str, List[float]] = {}
    for record in records:
        volume = _usable_volume(record)
        if volume is None:
            continue
        if not record.utility_name:
            continue
        groups.setdefault(record.utility_name, []).append(volume)
    return _summaries_from_groups(groups)


def summarize_volume_by_county(records: Iterable[SSORecord]) -> List[GroupVolumeSummary]:
    groups: Dict[str, List[float]] = {}
    for record in records:
        volume = _usable_volume(record)
        if volume is None:
            continue
        if not record.county:
            continue
        groups.setdefault(record.county, []).append(volume)
    return _summaries_from_groups(groups)


def summarize_volume_by_month(records: Iterable[SSORecord]) -> List[GroupVolumeSummary]:
    groups: Dict[str, List[float]] = {}
    for record in records:
        volume = _usable_volume(record)
        if volume is None:
            continue
        if not record.date_sso_began:
            continue
        key = record.date_sso_began.strftime("%Y-%m")
        groups.setdefault(key, []).append(volume)
    return _summaries_from_groups(groups)


def time_series_by_date(records: Iterable[SSORecord]) -> List[DateSeriesPoint]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for record in records:
        if not record.date_sso_began:
            continue
        key = record.date_sso_began.strftime("%Y-%m-%d")
        bucket = buckets.setdefault(key, {"count": 0, "volumes": []})
        bucket["count"] += 1
        volume = _usable_volume(record)
        if volume is not None:
            bucket["volumes"].append(volume)

    points: List[DateSeriesPoint] = []
    for key in sorted(buckets.keys()):
        volumes = buckets[key]["volumes"]
        total_volume = float(sum(volumes)) if volumes else 0.0
        points.append(
            DateSeriesPoint(
                date=key,
                count=buckets[key]["count"],
                total_volume_gallons=total_volume,
            )
        )
    return points


def _duration_hours(record: SSORecord) -> Optional[float]:
    if record.date_sso_began and record.date_sso_stopped:
        delta = record.date_sso_stopped - record.date_sso_began
        hours = delta.total_seconds() / 3600.0
        return hours if hours >= 0 else 0.0
    return None


def _month_key(record: SSORecord) -> Optional[str]:
    if not record.date_sso_began:
        return None
    return record.date_sso_began.strftime("%Y-%m")


def summarize_by_month(records: Sequence[SSORecord]) -> List[Dict[str, Any]]:
    """Aggregate spill counts and volumes by month (YYYY-MM).

    Records without a ``date_sso_began`` are skipped because the month bucket
    cannot be determined. ``total_volume`` sums valid, non-negative volume
    values and ignores ``None`` or negative entries.
    """

    buckets: Dict[str, Dict[str, Any]] = {}
    for record in records:
        month = _month_key(record)
        if not month:
            continue
        bucket = buckets.setdefault(month, {"spill_count": 0, "volumes": []})
        bucket["spill_count"] += 1
        volume = _usable_volume(record)
        if volume is not None:
            bucket["volumes"].append(volume)

    rows: List[Dict[str, Any]] = []
    for month in sorted(buckets.keys()):
        volumes = buckets[month]["volumes"]
        total_volume = float(sum(volumes)) if volumes else 0.0
        avg_volume = mean(volumes) if volumes else None
        max_volume = max(volumes) if volumes else None
        rows.append(
            {
                "month": month,
                "spill_count": buckets[month]["spill_count"],
                "total_volume": total_volume,
                "avg_volume": avg_volume,
                "max_volume": max_volume,
            }
        )
    return rows


def _utility_group_key(record: SSORecord) -> Optional[str]:
    if record.utility_id:
        return record.utility_id
    if record.utility_name:
        return record.utility_name
    return None


def summarize_by_utility(records: Sequence[SSORecord]) -> List[Dict[str, Any]]:
    """Summarize spills grouped by utility id/name.

    The grouping key prefers ``utility_id`` when available; otherwise it falls
    back to ``utility_name``. Records missing both are ignored. Results are
    sorted by ``total_volume`` descending and then by ``spill_count``.
    """

    buckets: Dict[str, Dict[str, Any]] = {}
    for record in records:
        group_key = _utility_group_key(record)
        if not group_key:
            continue
        bucket = buckets.setdefault(
            group_key,
            {
                "utility_id": record.utility_id,
                "utility_name": record.utility_name,
                "spill_count": 0,
                "volumes": [],
            },
        )
        # Preserve a readable utility_name even when grouped by ID only
        if not bucket.get("utility_name") and record.utility_name:
            bucket["utility_name"] = record.utility_name

        bucket["spill_count"] += 1
        volume = _usable_volume(record)
        if volume is not None:
            bucket["volumes"].append(volume)

    rows: List[Dict[str, Any]] = []
    for key, data in buckets.items():
        volumes = data["volumes"]
        total_volume = float(sum(volumes)) if volumes else 0.0
        avg_volume = mean(volumes) if volumes else None
        max_volume = max(volumes) if volumes else None
        rows.append(
            {
                "utility_id": data.get("utility_id"),
                "utility_name": data.get("utility_name") or key,
                "spill_count": data["spill_count"],
                "total_volume": total_volume,
                "avg_volume": avg_volume,
                "max_volume": max_volume,
            }
        )

    rows.sort(
        key=lambda row: (
            -row["total_volume"],
            -row["spill_count"],
            row.get("utility_name") or "",
        )
    )
    return rows


def _bucket_label(lower: float, upper: Optional[float]) -> str:
    if upper is None:
        return f">={lower:,.0f}"
    return f"{lower:,.0f}–{upper:,.0f}"


def summarize_by_volume_bucket(records: Sequence[SSORecord]) -> List[Dict[str, Any]]:
    """Summarize spill counts and volumes grouped into size buckets.

    Records with missing or negative volumes are assigned to an ``unknown``
    bucket to avoid losing count information.
    """

    buckets: Dict[str, Dict[str, Any]] = {}
    for lower, upper in VOLUME_BUCKETS:
        label = _bucket_label(lower, upper)
        buckets[label] = {"spill_count": 0, "total_volume": 0.0}
    buckets["unknown"] = {"spill_count": 0, "total_volume": 0.0}

    for record in records:
        volume = _usable_volume(record)
        if volume is None:
            buckets["unknown"]["spill_count"] += 1
            continue

        matched_label = None
        for lower, upper in VOLUME_BUCKETS:
            if upper is None:
                if volume >= lower:
                    matched_label = _bucket_label(lower, upper)
                    break
            elif lower <= volume < upper:
                matched_label = _bucket_label(lower, upper)
                break

        if matched_label is None:
            matched_label = "unknown"

        buckets[matched_label]["spill_count"] += 1
        buckets[matched_label]["total_volume"] += volume if volume is not None else 0.0

    rows: List[Dict[str, Any]] = []
    for lower, upper in VOLUME_BUCKETS:
        label = _bucket_label(lower, upper)
        rows.append({"bucket_label": label, **buckets[label]})
    rows.append({"bucket_label": "unknown", **buckets["unknown"]})
    return rows


def _date_bounds(records: Sequence[SSORecord]) -> tuple[Optional[datetime], Optional[datetime]]:
    dates = [record.date_sso_began for record in records if record.date_sso_began]
    if not dates:
        return None, None
    return min(dates), max(dates)


def build_time_series(records: Sequence[SSORecord]) -> Dict[str, Any]:
    min_date, max_date = _date_bounds(records)
    if not min_date or not max_date:
        return {"granularity": "none", "points": []}

    span_days = (max_date.date() - min_date.date()).days
    if span_days < 60:
        return {"granularity": "none", "points": []}

    if min_date.year != max_date.year:
        granularity = "year"
    else:
        granularity = "month"

    buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        if not record.date_sso_began:
            continue
        dt = record.date_sso_began
        if granularity == "year":
            key = str(dt.year)
            period_start = datetime(dt.year, 1, 1)
        else:
            key = f"{dt.year:04d}-{dt.month:02d}"
            period_start = datetime(dt.year, dt.month, 1)
        bucket = buckets.setdefault(
            key,
            {
                "period_label": key,
                "period_start": period_start.date().isoformat(),
                "spill_count": 0,
                "total_volume_gallons": 0.0,
            },
        )
        bucket["spill_count"] += 1
        volume = _best_volume(record)
        bucket["total_volume_gallons"] += volume if volume is not None else 0.0

    points = [buckets[key] for key in sorted(buckets.keys())]
    return {"granularity": granularity, "points": points}


def summarize_top_utilities(records: Sequence[SSORecord]) -> List[Dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for record in records:
        key = _utility_group_key(record)
        if not key:
            continue
        bucket = buckets.setdefault(
            key,
            {
                "utility_id": record.utility_id or key,
                "utility_name": record.utility_name or key,
                "spill_count": 0,
                "total_volume_gallons": 0.0,
            },
        )
        bucket["spill_count"] += 1
        volume = _best_volume(record)
        bucket["total_volume_gallons"] += volume if volume is not None else 0.0

    rows = list(buckets.values())
    rows.sort(
        key=lambda row: (
            -row["total_volume_gallons"],
            -row["spill_count"],
            row.get("utility_name") or "",
        )
    )
    return rows


def summarize_top_receiving_waters(records: Sequence[SSORecord]) -> List[Dict[str, Any]]:
    return summarize_by_receiving_water(records)


def summarize_by_receiving_water(
    records: Sequence[SSORecord], *, top_n: Optional[int] = None
) -> List[Dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}

    for record in records:
        name = _normalize_receiving_water_name(record.receiving_water)
        label = name or "Unknown"
        bucket = buckets.setdefault(
            label,
            {
                "name": label,
                "receiving_water": label,
                "receiving_water_name": label,
                "spill_count": 0,
                "total_volume_gallons": 0.0,
            },
        )
        bucket["spill_count"] += 1
        volume = _best_volume(record)
        bucket["total_volume_gallons"] += volume if volume is not None else 0.0

    rows = list(buckets.values())
    rows.sort(
        key=lambda row: (
            -row["total_volume_gallons"],
            -row["spill_count"],
            row.get("receiving_water_name") or "",
        )
    )
    if top_n is not None:
        rows = rows[:top_n]
    return rows


def _pie(entries: List[Dict[str, Any]], total_volume: float, *, key: str) -> List[Dict[str, Any]]:
    if not total_volume or total_volume <= 0:
        return []
    top_entries = entries[:10]
    pie: List[Dict[str, Any]] = []
    for entry in top_entries:
        volume = float(entry.get(key, 0.0) or 0.0)
        percent = (volume / total_volume) * 100 if total_volume else 0.0
        pie.append({**entry, "percent_of_total": percent})
    return pie


def build_utility_pie(entries: List[Dict[str, Any]], total_volume: float) -> List[Dict[str, Any]]:
    return _pie(entries, total_volume, key="total_volume_gallons")


def build_receiving_water_pie(
    entries: List[Dict[str, Any]], total_volume: float
) -> List[Dict[str, Any]]:
    return _pie(entries, total_volume, key="total_volume_gallons")


def build_dashboard_summary(
    records: Sequence[SSORecord], *, date_range: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    """Build a dashboard-friendly summary payload."""

    volumes = [vol for vol in (_best_volume(record) for record in records) if vol is not None]
    total_volume = float(sum(volumes)) if volumes else 0.0
    avg_volume = mean(volumes) if volumes else None
    max_volume = max(volumes) if volumes else None

    utilities = set()
    receiving_waters = set()
    duration_hours: list[float] = []
    for record in records:
        key = _utility_group_key(record)
        if key:
            utilities.add(key)
        if record.receiving_water:
            receiving_waters.add(record.receiving_water)
        dur = _duration_hours(record)
        if dur is not None:
            duration_hours.append(dur)

    date_values = [record.date_sso_began for record in records if record.date_sso_began]
    date_min = min(date_values).date().isoformat() if date_values else None
    date_max = max(date_values).date().isoformat() if date_values else None

    if date_range is not None:
        date_min = date_range.get("min") or date_min
        date_max = date_range.get("max") or date_max

    time_series = build_time_series(records)
    top_utils = summarize_top_utilities(records)
    top_receiving = summarize_top_receiving_waters(records)
    by_receiving_water = summarize_by_receiving_water(records, top_n=10)

    payload: Dict[str, Any] = {
        "summary_counts": {
            "total_records": len(records),
            "total_spills": len(records),
            "total_volume_gallons": total_volume,
            "total_volume": total_volume,
            "total_duration_hours": float(sum(duration_hours)) if duration_hours else 0.0,
            "avg_volume": avg_volume,
            "max_volume": max_volume,
            "distinct_utilities": len(utilities),
            "distinct_receiving_waters": len(receiving_waters),
            "date_range": {"min": date_min, "max": date_max},
        },
        "time_series": time_series,
        "top_utilities": top_utils,
        "top_utilities_pie": build_utility_pie(top_utils, total_volume),
        "top_receiving_waters": top_receiving,
        "receiving_waters_pie": build_receiving_water_pie(
            top_receiving, total_volume
        ),
        "by_receiving_water": [
            {
                "name": item.get("name") or item.get("receiving_water_name"),
                "total_volume": item.get("total_volume_gallons", 0.0),
                "spills": item.get("spill_count", 0),
            }
            for item in by_receiving_water
        ],
        # Legacy fields kept for backward compatibility
        "by_month": summarize_by_month(records),
        "by_utility": summarize_by_utility(records),
        "by_volume_bucket": summarize_by_volume_bucket(records),
    }

    return payload


def _detect_volume_range_text(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key, value in raw.items():
        if not isinstance(value, str):
            continue
        value_lower = value.lower()
        if "gal" not in value_lower:
            continue
        if ("<" in value_lower or ">" in value_lower) and any(
            char.isdigit() for char in value_lower
        ):
            return {"field": key, "value": value}
    return None


def run_basic_qa(records: Iterable[SSORecord]) -> List[QAIssue]:
    issues: List[QAIssue] = []

    for record in records:
        volume = record.volume_gallons
        if volume is not None:
            if volume < 0:
                issues.append(
                    QAIssue(
                        severity="error",
                        code="NEGATIVE_VOLUME",
                        message="Volume is negative",
                        sso_id=record.sso_id,
                        extra={"volume_gallons": volume},
                    )
                )
            elif volume == 0:
                issues.append(
                    QAIssue(
                        severity="warning",
                        code="ZERO_VOLUME",
                        message="Volume is zero",
                        sso_id=record.sso_id,
                    )
                )

        if record.date_sso_began is None:
            issues.append(
                QAIssue(
                    severity="warning",
                    code="MISSING_START_DATE",
                    message="date_sso_began is missing",
                    sso_id=record.sso_id,
                )
            )

        if not record.utility_name:
            issues.append(
                QAIssue(
                    severity="warning",
                    code="MISSING_UTILITY",
                    message="utility_name is missing",
                    sso_id=record.sso_id,
                )
            )

        if record.x is None or record.y is None:
            issues.append(
                QAIssue(
                    severity="warning",
                    code="MISSING_GEOMETRY",
                    message="Missing x or y coordinate",
                    sso_id=record.sso_id,
                )
            )

        range_info = _detect_volume_range_text(record.raw)
        if range_info:
            issues.append(
                QAIssue(
                    severity="info",
                    code="VOLUME_RANGE_TEXT",
                    message="Possible volume range description in raw text",
                    sso_id=record.sso_id,
                    extra=range_info,
                )
            )

    return issues


def top_utilities_by_volume(records: Iterable[SSORecord], n: int = 10) -> List[GroupVolumeSummary]:
    summaries = summarize_volume_by_utility(records)
    return summaries[:n]


def top_spills_by_volume(records: Iterable[SSORecord], n: int = 10) -> List[SpillRecordSummary]:
    usable_records = [
        record
        for record in records
        if record.volume_gallons is not None and record.volume_gallons >= 0
    ]
    sorted_records = sorted(
        usable_records,
        key=lambda record: (
            -(record.volume_gallons or 0),
            record.sso_id or "",
            record.utility_name or "",
        ),
    )
    top_records = sorted_records[:n]
    return [
        SpillRecordSummary(
            sso_id=record.sso_id,
            utility_name=record.utility_name,
            county=record.county,
            date_sso_began=record.date_sso_began,
            volume_gallons=record.volume_gallons,
            description=record.location_desc,
        )
        for record in top_records
    ]
