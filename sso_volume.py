"""Helpers for parsing and normalizing estimated volume fields."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def _normalize_raw_value(raw: str) -> str:
    """Return a normalized representation for mapping lookups."""

    return re.sub(r"\s+", "", raw).lower()


_BUCKET_MAPPINGS = {
    "<=1,0": (0, 1_000),
    "<=1,000": (0, 1_000),
    "<=1000": (0, 1_000),
    "1,000<gall": (1_000, 10_000),
    "1000<gall": (1_000, 10_000),
    "10,000<gall": (10_000, 25_000),
    "10000<gall": (10_000, 25_000),
    "25,000<gall": (25_000, 50_000),
    "25000<gall": (25_000, 50_000),
    "50,000<gall": (50_000, 75_000),
    "50000<gall": (50_000, 75_000),
    "75,000<gall": (75_000, 100_000),
    "75000<gall": (75_000, 100_000),
    "75,000<gallo": (75_000, 100_000),
    "100,000<gall": (100_000, 250_000),
    "100000<gall": (100_000, 250_000),
    "250,000<gall": (250_000, 500_000),
    "250000<gall": (250_000, 500_000),
    "500,000<gall": (500_000, 750_000),
    "500000<gall": (500_000, 750_000),
    "750,000<gall": (750_000, 1_000_000),
    "750,000<gallo": (750_000, 1_000_000),
    "750000<gall": (750_000, 1_000_000),
}


def _bucket_label(lower: int, upper: Optional[int]) -> str:
    if upper is None:
        return f"\u2265 {lower:,}"
    if lower == 0:
        return f"0 - {upper:,}"
    return f"{lower:,} - {upper:,}"


def parse_est_volume(raw: Any) -> Tuple[Optional[int], bool, Optional[str]]:
    """Parse a raw estimated volume string into structured pieces.

    Returns a tuple of ``(est_volume_gal, is_range, range_label)`` where
    ``est_volume_gal`` represents the numeric estimate (upper bound for ranges).
    """

    if raw is None:
        return None, False, None

    try:
        raw_str = str(raw).strip()
    except Exception:  # pragma: no cover - extremely defensive
        return None, False, None

    if not raw_str:
        return None, False, None

    if re.fullmatch(r"[\d,\s]+", raw_str):
        return int(raw_str.replace(",", "")), False, None

    norm = _normalize_raw_value(raw_str)
    if norm in _BUCKET_MAPPINGS:
        lower, upper = _BUCKET_MAPPINGS[norm]
        return upper, True, _bucket_label(lower, upper)

    for key, (lower, upper) in _BUCKET_MAPPINGS.items():
        if norm.startswith(key):
            return upper, True, _bucket_label(lower, upper)

    numbers = [int(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", raw_str)]
    if len(numbers) >= 2:
        lower, upper = numbers[0], numbers[1]
        return upper, True, _bucket_label(lower, upper)
    if len(numbers) == 1:
        lower = numbers[0]
        return lower, True, _bucket_label(lower, None)

    logger.warning("Unrecognized estimated volume format: %s", raw_str)
    return None, True, raw_str


def enrich_est_volume_fields(record: Dict[str, Any]) -> None:
    """Add structured estimated volume fields onto a raw record dictionary."""

    raw_est_volume = record.get("est_volume")
    est_volume_gal, is_range, range_label = parse_est_volume(raw_est_volume)

    record["est_volume_gal"] = est_volume_gal
    record["est_volume_is_range"] = "Y" if is_range else "N"
    record["est_volume_range_label"] = range_label
