"""SSO ArcGIS client for downloading sanitary sewer overflow records."""
from __future__ import annotations

import logging
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
from sso_transform import PERMITTEE_MAP, simplify_permittee_name, generate_slug

DEFAULT_BASE_URL = "https://gis.adem.alabama.gov/arcgis/rest/services/SSOs_ALL_OB_ID/MapServer/0/query"
DEFAULT_PAGE_SIZE = 2000
MAX_REASONABLE_RECORDS = 250_000

logger = logging.getLogger(__name__)


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
        self._supports_pagination: Optional[bool] = None
        self._max_record_count: Optional[int] = None

        # SSL Configuration
        self.verify: bool | str = True
        
        # Priority 1: REQUESTS_CA_BUNDLE environment variable
        env_bundle = os.getenv("REQUESTS_CA_BUNDLE")
        if env_bundle:
            if os.path.exists(env_bundle):
                self.verify = env_bundle
                logger.info(f"Using SSL CA bundle from REQUESTS_CA_BUNDLE: {env_bundle}")
            else:
                logger.warning(f"REQUESTS_CA_BUNDLE set but path does not exist: {env_bundle}")

        # Priority 2: VERIFY_SSL explicitly disabled
        elif os.getenv("VERIFY_SSL", "").lower() == "false":
            self.verify = False
            logger.warning("SSL verification is explicitly disabled via VERIFY_SSL=false")
        
        else:
            # Priority 3: Search for ADEM CA chain in known locations
            script_dir = os.path.dirname(os.path.abspath(__file__))
            repo_root = os.path.abspath(os.path.join(script_dir, ".."))
            
            cert_paths = [
                os.path.join(script_dir, "adem_ca_chain.pem"), # scripts/adem_ca_chain.pem
                os.path.join(repo_root, "adem_ca_chain.pem"),  # root/adem_ca_chain.pem
                os.path.join(repo_root, "frontend", "adem_ca_chain.pem"), # frontend/adem_ca_chain.pem
                os.path.join(repo_root, "api", "adem_ca_chain.pem"), # api/adem_ca_chain.pem
                os.path.join(repo_root, "frontend", "api", "adem_ca_chain.pem"), # frontend/api/adem_ca_chain.pem
                "/var/task/adem_ca_chain.pem",
                "/var/task/api/adem_ca_chain.pem",
                "/var/task/frontend/adem_ca_chain.pem",
                "adem_ca_chain.pem",
            ]
            
            cert_found = False
            for path in cert_paths:
                if os.path.exists(path):
                    self.verify = path
                    logger.info(f"Using ADEM CA chain found at: {path}")
                    cert_found = True
                    break
            
            if not cert_found:
                # Fallback: In Vercel (/var/task exists), if we can't find our cert, 
                # we might have to disable verification or rely on system (which likely fails).
                if os.path.exists("/var/task"):
                    logger.error("Running on Vercel but adem_ca_chain.pem not found in any search path!")
                    # We'll leave self.verify = True (system default) but it will likely fail 
                    # if the server is still misconfigured.
                else:
                    logger.debug("No custom CA chain found; using system defaults.")

    def _get(self, params: Dict[str, Any], *, url: Optional[str] = None) -> Dict[str, Any]:
        response = self.session.get(
            url or self.base_url, 
            params=params, 
            timeout=self.timeout,
            verify=self.verify
        )
        if not response.ok:
            raise SSOClientError(
                f"Request failed with status {response.status_code}: {response.text[:200]}"
            )
        try:
            data = response.json()
            if "error" in data:
                err = data["error"]
                raise SSOClientError(
                    f"ArcGIS Error {err.get('code')}: {err.get('message')} - {err.get('details')}"
                )
            return data
        except ValueError as exc:  # pragma: no cover - defensive
            raise SSOClientError("Failed to decode JSON response") from exc

    def _load_layer_metadata(self) -> tuple[Optional[bool], Optional[int]]:
        if self._supports_pagination is not None and self._max_record_count is not None:
            return self._supports_pagination, self._max_record_count

        meta_url = self.base_url
        if meta_url.endswith("/query"):
            meta_url = meta_url[: -len("/query")]

        try:
            data = self._get({"f": "json"}, url=meta_url)
        except Exception:  # pragma: no cover - defensive
            return self._supports_pagination, self._max_record_count

        self._supports_pagination = bool(data.get("supportsPagination"))
        try:
            self._max_record_count = int(data.get("maxRecordCount")) if data.get("maxRecordCount") else None
        except (TypeError, ValueError):  # pragma: no cover - defensive
            self._max_record_count = None

        return self._supports_pagination, self._max_record_count

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

        supports_pagination, max_record_count = self._load_layer_metadata()

        offset = 0
        page_size = int(params.pop("resultRecordCount", DEFAULT_PAGE_SIZE))
        if max_record_count:
            page_size = min(page_size, int(max_record_count))
        records: List[Dict[str, Any]] = []

        while True:
            page_params = dict(params)
            if supports_pagination:
                page_params["resultOffset"] = offset
                page_params["resultRecordCount"] = page_size
            data = self._get(page_params)

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

            if limit is not None and len(records) >= limit:
                return records[:limit]

            if len(feature_list) < page_size:
                break

            if len(records) > MAX_REASONABLE_RECORDS:
                logger.warning(
                    "Fetched %s records which exceeds the expected upper bound.", len(records)
                )

            if not supports_pagination:
                break

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

    def _distinct_values(
        self, fields: list[str], *, order_by: str | None = None
    ) -> list[dict[str, Any]]:
        params: Dict[str, Any] = {
            "where": "1=1",
            "outFields": ",".join(fields),
            "returnDistinctValues": "true",
            "returnGeometry": "false",
            "f": "json",
        }
        if order_by:
            params["orderByFields"] = order_by
        data = self._get(params)
        feature_list: list[dict[str, Any]] = list(data.get("features", []) or [])
        values: list[dict[str, Any]] = []
        for feature in feature_list:
            attrs = dict(feature.get("attributes", {}))
            values.append(attrs)
        return values

    def list_utilities(self) -> list[dict[str, str]]:
        """Return distinct utilities available in the ArcGIS layer."""

        raw_utilities = self._distinct_values(
            [UTILITY_ID_FIELD, UTILITY_NAME_FIELD], order_by=UTILITY_NAME_FIELD
        )
        seen: dict[str, dict[str, str]] = {}
        for attrs in raw_utilities:
            utility_id = str(attrs.get(UTILITY_ID_FIELD) or "").strip()
            utility_name = str(attrs.get(UTILITY_NAME_FIELD) or "").strip()
            if not utility_id and not utility_name:
                continue
            key = utility_id or utility_name
            existing = seen.get(key)
            if existing:
                if utility_name and not existing.get("name"):
                    existing["name"] = utility_name
                continue
            seen[key] = {"id": utility_id or utility_name, "name": utility_name or utility_id}

        return sorted(seen.values(), key=lambda item: item["name"].lower())

    def permittee_permit_map(self) -> dict[str, dict[str, object]]:
        """Return a mapping of permittee name -> details about their permits."""

        raw = self._distinct_values([UTILITY_NAME_FIELD, UTILITY_ID_FIELD])
        mapping: dict[str, dict[str, object]] = {}
        for attrs in raw:
            name = str(attrs.get(UTILITY_NAME_FIELD) or "").strip()
            permit = str(attrs.get(UTILITY_ID_FIELD) or "").strip()

            # Apply canonical mapping for consistent permittee names
            if permit and permit in PERMITTEE_MAP:
                name = PERMITTEE_MAP[permit]
            elif name and name.lower() in PERMITTEE_MAP:
                name = PERMITTEE_MAP[name.lower()]

            # Simplify naming (e.g. City of X -> Utilities of X)
            name = simplify_permittee_name(name)

            if not name and not permit:
                continue
            key = (name or permit).lower()
            entry = mapping.setdefault(key, {"label": name or permit or key, "permits": set(), "aliases": set()})
            if name:
                entry["label"] = name
            if permit:
                entry["permits"].add(permit)
            
            # Store the original raw name as an alias for search matching
            raw_name = str(attrs.get(UTILITY_NAME_FIELD) or "").strip()
            if raw_name:
                entry["aliases"].add(raw_name)

        normalized: dict[str, dict[str, object]] = {}
        for key, entry in mapping.items():
            normalized[key] = {
                "label": entry["label"],
                "permits": sorted(entry["permits"]),
                "aliases": sorted(entry["aliases"]),
            }
        return normalized

    def list_permittees(self) -> list[dict[str, object]]:
        """Return permittee display metadata with their associated permits."""

        mapping = self.permittee_permit_map()
        rows: list[dict[str, object]] = []
        for key_lower, entry in mapping.items():
            permits = list(entry.get("permits") or [])
            if not permits:
                continue
            primary = permits[0]
            name = str(entry.get("label") or key_lower).strip() or key_lower.title()
            rows.append({
                "id": primary,
                "name": name,
                "slug": generate_slug(name),
                "permits": permits,
                "aliases": list(entry.get("aliases") or [])
            })

        rows.sort(key=lambda item: item["name"].lower())
        return rows

    def list_counties(self) -> list[str]:
        """Return distinct counties present in the ArcGIS layer."""

        raw_counties = self._distinct_values([COUNTY_FIELD], order_by=COUNTY_FIELD)
        counties: list[str] = []
        for attrs in raw_counties:
            county = str(attrs.get(COUNTY_FIELD) or "").strip()
            if not county:
                continue
            counties.append(county)
        counties = sorted(set(counties), key=lambda name: name.lower())
        return counties
