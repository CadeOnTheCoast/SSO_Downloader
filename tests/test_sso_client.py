from __future__ import annotations

import pytest

from sso_client import (
    COUNTY_FIELD,
    START_DATE_FIELD,
    SSOClient,
    SSOClientError,
    UTILITY_ID_FIELD,
    UTILITY_NAME_FIELD,
)
from sso_schema import SSOQuery


class DummyResponse:
    def __init__(self, json_data, status_code=200, text="") -> None:
        self._json_data = json_data
        self.status_code = status_code
        self.text = text or str(json_data)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


class MockSession:
    def __init__(self, responses: list[DummyResponse]) -> None:
        self.responses = responses
        self.calls = []

    def get(self, url, params=None, timeout=None):  # noqa: D401
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if not self.responses:
            raise AssertionError("No mock responses left")
        return self.responses.pop(0)


def test_build_where_clause():
    client = SSOClient(base_url="http://example.com")
    where = client._build_where_clause(
        utility_id="AL123'45",
        utility_name="Utility",
        county="Mobile",
        start_date="2024-01-01",
        end_date="2024-02-01",
    )

    assert "2024-02-02" in where
    assert f"{UTILITY_ID_FIELD} = 'AL123''45'" in where
    assert f"{UTILITY_NAME_FIELD} = 'Utility'" in where
    assert f"{COUNTY_FIELD} = 'Mobile'" in where


def test_fetch_ssos_paginates_and_applies_limit():
    responses = [
        DummyResponse({"supportsPagination": True, "maxRecordCount": 2}),
        DummyResponse({
            "features": [
                {"attributes": {"id": 1}, "geometry": {"x": 1, "y": 2}},
                {"attributes": {"id": 2}, "geometry": {"x": 3, "y": 4}},
            ]
        }),
        DummyResponse({
            "features": [
                {"attributes": {"id": 3}, "geometry": {"x": 5, "y": 6}},
            ]
        }),
    ]
    session = MockSession(responses)
    client = SSOClient(base_url="http://example.com", session=session)

    records = client.fetch_ssos(limit=2, extra_params={"resultRecordCount": 2})

    assert len(records) == 2
    assert records[0]["id"] == 1
    assert session.calls[1]["params"]["resultOffset"] == 0
    # Limit should stop further pagination once enough records are collected
    assert len(session.calls) == 2


def test_fetch_ssos_handles_http_error():
    session = MockSession(
        [DummyResponse({"supportsPagination": True}), DummyResponse({}, status_code=500, text="boom")]
    )
    client = SSOClient(base_url="http://example.com", session=session)

    with pytest.raises(SSOClientError):
        client.fetch_ssos()


def test_fetch_ssos_invalid_json():
    session = MockSession([DummyResponse({"supportsPagination": True}), DummyResponse(ValueError("bad json"))])
    client = SSOClient(base_url="http://example.com", session=session)

    with pytest.raises(SSOClientError):
        client.fetch_ssos()


def test_fetch_ssos_accepts_query_object():
    responses = [
        DummyResponse({"supportsPagination": True}),
        DummyResponse({
            "features": [
                {"attributes": {"id": 1}, "geometry": {"x": 1, "y": 2}},
            ]
        }),
    ]
    session = MockSession(responses)
    client = SSOClient(base_url="http://example.com", session=session)
    query = SSOQuery(county="Mobile")

    records = client.fetch_ssos(query=query, limit=1)

    assert len(records) == 1
    assert "where" in session.calls[1]["params"]
    assert "county = 'Mobile'" in session.calls[1]["params"]["where"]


def test_fetch_ssos_collects_all_pages_when_no_limit():
    responses = [
        DummyResponse({"supportsPagination": True, "maxRecordCount": 2}),
        DummyResponse(
            {
                "features": [
                    {"attributes": {"id": 1}, "geometry": {"x": 1, "y": 1}},
                    {"attributes": {"id": 2}, "geometry": {"x": 2, "y": 2}},
                ]
            }
        ),
        DummyResponse(
            {
                "features": [
                    {"attributes": {"id": 3}, "geometry": {"x": 3, "y": 3}},
                ]
            }
        ),
    ]
    session = MockSession(responses)
    client = SSOClient(base_url="http://example.com", session=session)

    records = client.fetch_ssos(extra_params={"resultRecordCount": 2})

    assert len(records) == 3
    assert session.calls[1]["params"]["resultOffset"] == 0
    assert session.calls[2]["params"]["resultOffset"] == 2
