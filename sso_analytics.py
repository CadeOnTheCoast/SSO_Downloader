"""Analytics and QA helpers for SSO records."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional
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
