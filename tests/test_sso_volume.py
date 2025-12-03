import pytest
from datetime import datetime

from sso_analytics import build_dashboard_summary
from sso_schema import START_DATE_FIELD, normalize_sso_records
from sso_volume import enrich_est_volume_fields, parse_est_volume


@pytest.mark.parametrize(
    "raw, expected_gal, is_range, label",
    [
        ("25,000", 25000, False, None),
        ("<=1,0", 1000, True, "0 - 1,000"),
        ("1,000 < gall", 10000, True, "1,000 - 10,000"),
        ("10,000 < gall", 25000, True, "10,000 - 25,000"),
        ("250,000 < gall", 500000, True, "250,000 - 500,000"),
        ("500,000 < gall", 750000, True, "500,000 - 750,000"),
        ("750,000 < gallo", 1_000_000, True, "750,000 - 1,000,000"),
        ("1,000,000 < gall", 1_000_000, True, "≥ 1,000,000"),
    ],
)
def test_parse_est_volume_cases(raw, expected_gal, is_range, label):
    est_volume_gal, parsed_is_range, range_label = parse_est_volume(raw)
    assert est_volume_gal == expected_gal
    assert parsed_is_range is is_range
    assert range_label == label


def test_dashboard_summary_uses_estimated_volume_upper_bound():
    raw_records = [
        {"est_volume": "10,000 < gall", START_DATE_FIELD: datetime(2024, 1, 1)},
        {"est_volume": "25,000", START_DATE_FIELD: datetime(2024, 1, 2)},
        {"est_volume": "250,000 < gall", START_DATE_FIELD: datetime(2024, 2, 1)},
        {"est_volume": None, START_DATE_FIELD: datetime(2024, 2, 5)},
    ]

    for record in raw_records:
        enrich_est_volume_fields(record)

    records = normalize_sso_records(raw_records)
    summary = build_dashboard_summary(records)

    assert summary["summary_counts"]["total_volume_gallons"] == 550_000
    assert summary["summary_counts"]["max_volume"] == 500_000
    assert summary["summary_counts"]["avg_volume"] == pytest.approx(183_333.3333, rel=1e-6)
    assert all(item.get("total_volume") for item in summary["by_month"])
