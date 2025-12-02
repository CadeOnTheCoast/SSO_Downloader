from datetime import datetime
from typing import List

from fastapi.testclient import TestClient

from sso_schema import (
    COUNTY_FIELD,
    START_DATE_FIELD,
    UTILITY_NAME_FIELD,
    VOLUME_GALLONS_FIELD,
)
from webapp import api


class DummyClient:
    def __init__(self, records: List[dict]):
        self.records = records
        self.last_limit = None

    def fetch_ssos(self, query=None, limit=None, **kwargs):
        self.last_limit = limit
        if limit is not None:
            return list(self.records)[:limit]
        return list(self.records)


def _set_client_override(records: List[dict]) -> TestClient:
    dummy = DummyClient(records)
    api.app.dependency_overrides[api.get_client] = lambda: dummy
    return TestClient(api.app), dummy


def _clear_overrides() -> None:
    api.app.dependency_overrides = {}


def test_series_by_date_returns_points_and_enforces_limit():
    records = [
        {START_DATE_FIELD: datetime(2024, 1, 1), VOLUME_GALLONS_FIELD: 100.0},
        {START_DATE_FIELD: datetime(2024, 1, 1), VOLUME_GALLONS_FIELD: 50.0},
        {START_DATE_FIELD: datetime(2024, 1, 2), VOLUME_GALLONS_FIELD: 75.0},
    ]
    client, dummy = _set_client_override(records)

    response = client.get("/series/by_date", params={"start_date": "2024-01-01"})
    _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert "points" in payload
    assert payload["points"][0]["date"] == "2024-01-01"
    assert payload["points"][0]["count"] == 2
    assert dummy.last_limit == 5000  # default bounded limit


def test_series_by_utility_returns_bars():
    records = [
        {
            START_DATE_FIELD: datetime(2024, 1, 1),
            UTILITY_NAME_FIELD: "Utility A",
            VOLUME_GALLONS_FIELD: 100.0,
        },
        {
            START_DATE_FIELD: datetime(2024, 1, 2),
            UTILITY_NAME_FIELD: "Utility B",
            VOLUME_GALLONS_FIELD: 50.0,
        },
        {
            START_DATE_FIELD: datetime(2024, 1, 3),
            UTILITY_NAME_FIELD: "Utility A",
            VOLUME_GALLONS_FIELD: 25.0,
        },
    ]
    client, dummy = _set_client_override(records)

    response = client.get("/series/by_utility", params={"county": "Mobile", "limit": 20000})
    _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert "bars" in payload
    labels = [bar["label"] for bar in payload["bars"]]
    assert "Utility A" in labels
    assert dummy.last_limit == 10000  # capped at maximum


def test_records_endpoint_returns_serialized_rows():
    records = [
        {
            START_DATE_FIELD: datetime(2024, 1, 1),
            UTILITY_NAME_FIELD: "Utility A",
            COUNTY_FIELD: "Mobile",
            VOLUME_GALLONS_FIELD: 100.0,
        }
    ]
    client, dummy = _set_client_override(records)

    response = client.get(
        "/records", params={"utility_name": "Utility A", "limit": 5, "offset": 0}
    )
    _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert "records" in payload
    assert payload["records"][0]["utility_name"] == "Utility A"
    assert payload["total"] == 1
    assert dummy.last_limit == 5


def test_dashboard_template_renders():
    client, _dummy = _set_client_override([])
    response = client.get("/dashboard")
    _clear_overrides()

    assert response.status_code == 200
    assert "summary-total-count" in response.text
    assert "time-series-chart" in response.text
