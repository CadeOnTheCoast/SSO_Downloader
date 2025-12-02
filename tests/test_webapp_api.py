from __future__ import annotations

from datetime import datetime
from typing import List

from fastapi.testclient import TestClient

from datetime import datetime
from typing import List

from fastapi.testclient import TestClient

from sso_schema import (
    COUNTY_FIELD,
    START_DATE_FIELD,
    UTILITY_ID_FIELD,
    UTILITY_NAME_FIELD,
    VOLUME_GALLONS_FIELD,
)
from webapp import api


class DummyClient:
    def __init__(self, records: List[dict]):
        self.records = records

    def fetch_ssos(self, query=None, limit=None, **kwargs):  # pragma: no cover - simple stub
        if limit is not None:
            return self.records[:limit]
        return list(self.records)


def _set_client_override(records: List[dict]) -> TestClient:
    dummy = DummyClient(records)
    api.app.dependency_overrides[api.get_client] = lambda: dummy
    return TestClient(api.app)


def _clear_overrides() -> None:
    api.app.dependency_overrides = {}


def test_health_check():
    client = _set_client_override([])
    response = client.get("/health")
    _clear_overrides()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_filters_endpoint_structure():
    client = _set_client_override([])
    response = client.get("/filters")
    _clear_overrides()

    payload = response.json()
    assert "utilities" in payload
    assert "counties" in payload
    assert isinstance(payload["utilities"], list)
    assert isinstance(payload["counties"], list)


def test_download_returns_csv_and_filename(tmp_path):
    records = [
        {
            UTILITY_ID_FIELD: "AL1234567",
            UTILITY_NAME_FIELD: "Sample Utility",
            COUNTY_FIELD: "Mobile",
            START_DATE_FIELD: datetime(2024, 1, 1),
            VOLUME_GALLONS_FIELD: 100.0,
        }
    ]
    client = _set_client_override(records)

    response = client.get("/download", params={"utility_id": "AL1234567"})
    _clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    disposition = response.headers["content-disposition"]
    assert "AL1234567" in disposition
    assert "attachment" in disposition
    assert UTILITY_ID_FIELD in response.text
    assert "Sample Utility" in response.text


def test_download_requires_filters():
    client = _set_client_override([])
    response = client.get("/download")
    _clear_overrides()

    assert response.status_code == 400
    assert "At least one filter" in response.json()["detail"]


def test_dashboard_summary_returns_expected_payload():
    records = [
        {
            UTILITY_ID_FIELD: "AL1234567",
            UTILITY_NAME_FIELD: "Utility A",
            COUNTY_FIELD: "Mobile",
            START_DATE_FIELD: datetime(2024, 1, 1),
            VOLUME_GALLONS_FIELD: 100.0,
        },
        {
            UTILITY_ID_FIELD: "AL7654321",
            UTILITY_NAME_FIELD: "Utility B",
            COUNTY_FIELD: "Mobile",
            START_DATE_FIELD: datetime(2024, 2, 1),
            VOLUME_GALLONS_FIELD: 50.0,
        },
    ]
    client = _set_client_override(records)

    response = client.get("/api/ssos/summary", params={"utility_id": "AL1234567"})
    _clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary_counts"]["total_records"] == 2
    assert payload["summary_counts"]["total_volume"] == 150.0
    assert payload["by_month"]
    assert payload["by_utility"]
    assert payload["by_volume_bucket"]
