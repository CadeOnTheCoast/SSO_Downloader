# SSO downloader architecture and wiring map

This note summarizes the key modules, functions, and their relationships so wiring issues are easy to spot.

## Core backend modules

| Module | Location | Purpose | Key functions/classes | Imported by |
| --- | --- | --- | --- | --- |
| `sso_client` | `sso_client.py` | Low-level ArcGIS REST client that pages through features and flattens geometry onto attributes. | `SSOClient` (constructor accepts base URL/API key/timeout), `SSOClient.fetch_ssos(query, limit, **kwargs)`, `SSOClientError` | `webapp/api.py`, CLI scripts |
| `sso_schema` | `sso_schema.py` | Canonical record model and query builder shared by client, API, and analytics. | `SSORecord` dataclass, `normalize_sso_record`, `normalize_sso_records`, `SSOQuery` (with `validate`, `build_where_clause`, `to_query_params`) | `sso_client`, `sso_analytics`, `webapp/api.py` |
| `sso_transform` | *(not present; normalization lives in `sso_schema`)* | — | — | — |
| `sso_export` | `sso_export.py` | CSV serialization helpers for normalized/raw SSO dictionaries. | `write_ssos_to_csv_filelike(records, handle)`, `write_ssos_to_csv(records, path)` | `webapp/api.py`, CLI scripts |
| `sso_analytics` | `sso_analytics.py` | Aggregations and QA helpers over normalized records. | `build_dashboard_summary`, `summarize_by_month`, `summarize_by_utility`, `summarize_by_volume_bucket`, `summarize_volume_by_utility`, `time_series_by_date`, QA helpers | `webapp/api.py` |

## HTTP API (FastAPI)

* Entrypoint: `webapp/api.py` (`create_app()` returns the `FastAPI` instance). Static files/templates live under `webapp/static` and `webapp/templates`.
* Routes:
  * `/health` – simple status JSON.
  * `/filters` & `/api/options` – filter metadata for UI dropdowns (utilities + counties).
  * `/` – download page (`index.html`).
  * `/download` & `/api/ssos.csv` – CSV export using `write_ssos_to_csv_filelike`; enforces at least one filter.
  * `/api/ssos/summary` & `/summary` – dashboard summary built from `build_dashboard_summary(normalize_sso_records(...))`.
  * `/series/by_date` – time series using `time_series_by_date`.
  * `/series/by_utility` – grouped volume bars via `summarize_volume_by_utility`.
  * `/records` – paginated records for legacy consumers.
  * `/api/ssos` – normalized record list for the dashboard table (supports `limit`/`offset`).
* Shared request models:
  * `SSOQueryParams` (utility_id, utility_name, county, start_date, end_date, limit) with `to_sso_query()` and `bounded_limit()`.
  * `RecordsQueryParams` extends `SSOQueryParams` with `offset` and default/maximum limits for table endpoints.

## Frontend

* Download page (`webapp/templates/index.html`): fetches `/api/options` (fallback `/filters`) to populate filters; downloads CSV via `/api/ssos.csv`; preview summary via `/api/ssos/summary` (fallback `/summary`).
* Dashboard page (`webapp/templates/dashboard.html` + `webapp/static/dashboard.js`):
  * Fetches filters from `/api/options` (fallback `/filters`).
  * Calls `/api/ssos/summary` for headline stats and charts, `/api/ssos` for the table, and uses the same query string for `/api/ssos.csv` downloads.
  * Expects summary payload keys: `summary_counts` (includes `total_records`, `total_volume`, `avg_volume`, `max_volume`, `distinct_utilities`, `date_range`), `by_month` (month, spill_count, total_volume, avg_volume, max_volume), `by_utility` (utility_id/name, spill_count, total_volume, avg_volume, max_volume), and `by_volume_bucket` (bucket_label, spill_count, total_volume).

Use this map when reviewing imports, query parameter wiring, and response shapes between layers.
