from __future__ import annotations

from datetime import date, datetime

import pytest

from sso_schema import (
    SSOQuery,
    SSORecord,
    normalize_sso_record,
    normalize_sso_records,
)


def test_normalize_sso_record_parses_fields():
    raw = {
        "sso_id": "123",
        "permit_no": "AL1234567",
        "permittee": "Utility Name",
        "sewer_system": "Combined",
        "county": "Mobile",
        "location": "Main St",
        "date_sso_began": 1_700_000_000_000,  # epoch ms
        "date_sso_stopped": "2023-11-02 05:00:00",
        "volume_gallons": "42.5",
        "cause": "Blockage",
        "receiving_water": "River",
        "x": "-86.123",
        "y": 32.456,
        "unexpected": "keep me",
    }

    record = normalize_sso_record(raw)

    assert isinstance(record, SSORecord)
    assert record.sso_id == "123"
    assert record.utility_id == "AL1234567"
    assert record.utility_name == "Utility Name"
    assert record.sewer_system == "Combined"
    assert record.county == "Mobile"
    assert record.location_desc == "Main St"
    assert isinstance(record.date_sso_began, datetime)
    assert record.date_sso_began.year == 2023
    assert isinstance(record.date_sso_stopped, datetime)
    assert record.volume_gallons == 42.5
    assert record.cause == "Blockage"
    assert record.receiving_water == "River"
    assert record.x == -86.123
    assert record.y == 32.456
    assert record.raw["unexpected"] == "keep me"


def test_normalize_sso_records_preserves_order():
    raws = [{"sso_id": "1"}, {"sso_id": "2"}]

    records = normalize_sso_records(raws)

    assert [record.sso_id for record in records] == ["1", "2"]


def test_sso_query_builds_where_clause():
    query = SSOQuery(
        county="Mobile",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        min_volume_gallons=10,
        max_volume_gallons=100,
    )

    where = query.build_where_clause()

    assert "date_sso_began >= DATE '2024-01-01 00:00:00'" in where
    assert "date_sso_began < DATE '2024-02-01 00:00:00'" in where
    assert "volume_gallons >= 10" in where
    assert "volume_gallons <= 100" in where
    assert "county = 'Mobile'" in where


def test_sso_query_to_query_params_adds_extra_params():
    query = SSOQuery(county="Mobile", extra_params={"resultRecordCount": 50})

    params = query.to_query_params()

    assert "where" in params
    assert params["orderByFields"] == "date_sso_began"
    assert params["resultRecordCount"] == 50


@pytest.mark.parametrize(
    "query_args",
    [
        {"start_date": date(2024, 2, 1), "end_date": date(2024, 1, 1)},
        {"min_volume_gallons": -1},
        {"max_volume_gallons": -1},
        {"min_volume_gallons": 10, "max_volume_gallons": 5},
    ],
)
def test_sso_query_validate_raises(query_args):
    query = SSOQuery(**query_args)

    with pytest.raises(ValueError):
        query.validate()
