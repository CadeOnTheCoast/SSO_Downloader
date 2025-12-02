"""SSO ArcGIS client for downloading sanitary sewer overflow records."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from sso_schema import (
    COUNTY_FIELD,
    END_DATE_FIELD,
    START_DATE_FIELD,
    UTILITY_ID_FIELD,
    UTILITY_NAME_FIELD,
    SSOQuery,
)

DEFAULT_BASE_URL = "https://gis.adem.alabama.gov/arcgis/rest/services/SSOs_ALL_OB_ID/MapServer/0/query"
DEFAULT_PAGE_SIZE = 2000


class SSOClientError(RuntimeError):
    """Error raised for SSO client failures."""


@dataclass
class SSOClientConfig:
    base_url: str = DEFAULT_BASE_URL
    api_key: Optional[str] = None
    timeout: int = 30

    @classmethod
    def from_env(cls) -> "SSOClientConfig":
        return cls(
            base_url=os.getenv("SSO_API_BASE_URL", DEFAULT_BASE_URL),
            api_key=os.getenv("SSO_API_KEY"),
            timeout=int(os.getenv("SSO_API_TIMEOUT", "30")),
        )


class SSOClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
        session: requests.Session | None = None,
    ) -> None:
        config = SSOClientConfig.from_env()
        self.base_url = base_url or config.base_url
        self.api_key = api_key or config.api_key
        self.timeout = timeout if timeout is not None else config.timeout
        self.session = session or requests.Session()

    def fetch_ssos(
        self,
        query: SSOQuery | None = None,
        utility_id: str | None = None,
        utility_name: str | None = None,
        county: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        extra_params: dict | None = None,
    ) -> list[dict]:
        params: Dict[str, Any] = {
            "outFields": "*",
            "f": "json",
        }

        query_obj = query or self._build_query(
            utility_id=utility_id,
            utility_name=utility_name,
            county=county,
            start_date=start_date,
            end_date=end_date,
            extra_params=extra_params,
        )
        params.update(query_obj.to_query_params())
        if self.api_key:
            params["token"] = self.api_key
        if extra_params and not query_obj.extra_params:
            params.update(extra_params)

        offset = 0
        page_size = int(params.pop("resultRecordCount", DEFAULT_PAGE_SIZE))
        records: List[Dict[str, Any]] = []

        while True:
            page_params = dict(params)
            page_params["resultOffset"] = offset
            page_params["resultRecordCount"] = page_size
            response = self.session.get(self.base_url, params=page_params, timeout=self.timeout)
            if not response.ok:
                raise SSOClientError(
                    f"Request failed with status {response.status_code}: {response.text[:200]}"
                )
            try:
                data = response.json()
            except ValueError as exc:
                raise SSOClientError("Failed to decode JSON response") from exc

            feature_list: List[Dict[str, Any]] = list(data.get("features", []) or [])
            if not feature_list:
                break

            for feature in feature_list:
                attrs = dict(feature.get("attributes", {}))
                geometry = feature.get("geometry") or {}
                attrs["x"] = geometry.get("x")
                attrs["y"] = geometry.get("y")
                records.append(attrs)
                if limit is not None and len(records) >= limit:
                    return records[:limit]

            offset += len(feature_list)

        return records

    def _build_where_clause(
        self,
        utility_id: str | None,
        utility_name: str | None,
        county: str | None,
        start_date: str | None,
        end_date: str | None,
    ) -> str:
        query_obj = self._build_query(
            utility_id=utility_id,
            utility_name=utility_name,
            county=county,
            start_date=start_date,
            end_date=end_date,
        )
        return query_obj.build_where_clause()

    def _build_query(
        self,
        utility_id: str | None,
        utility_name: str | None,
        county: str | None,
        start_date: str | None,
        end_date: str | None,
        extra_params: dict | None = None,
    ) -> SSOQuery:
        start = None
        end = None
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return SSOQuery(
            utility_id=utility_id,
            utility_name=utility_name,
            county=county,
            start_date=start,
            end_date=end,
            extra_params=extra_params,
        )
