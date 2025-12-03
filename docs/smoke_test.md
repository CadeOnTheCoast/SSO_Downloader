# Smoke test checklist (SSO downloader)

Quick steps for verifying the API and dashboard wiring without hitting production ArcGIS aggressively.

## Backend API

1. Start the app locally:
   ```bash
   uvicorn webapp.api:app --reload
   ```
2. Call the JSON endpoint with a small filter:
   ```bash
   curl "http://127.0.0.1:8000/api/ssos?utility_id=AL0046744&start_date=2024-01-01&end_date=2024-01-31&limit=5"
   ```
   Confirm you see `items`, `total`, `offset`, and `limit` keys with ISO-formatted dates.
3. Fetch the summary for the same filters:
   ```bash
   curl "http://127.0.0.1:8000/api/ssos/summary?utility_id=AL0046744&start_date=2024-01-01&end_date=2024-01-31"
   ```
   Confirm `summary_counts`, `by_month`, `by_utility`, and `by_volume_bucket` keys are present.
4. Download CSV to a temp file and open the header:
   ```bash
   curl -L -o /tmp/ssos.csv "http://127.0.0.1:8000/api/ssos.csv?utility_id=AL0046744&start_date=2024-01-01&end_date=2024-01-31"
   head -n 5 /tmp/ssos.csv
   ```

## Frontend

1. Open `http://127.0.0.1:8000/`.
   * Load filter dropdowns from `/api/options`.
   * Add a utility/date filter and click **Download CSV** – URL should point to `/api/ssos.csv`.
   * Click **Preview summary** – response should come from `/api/ssos/summary`.
2. Open `http://127.0.0.1:8000/dashboard`.
   * Apply filters and confirm headline stats populate.
   * Charts should render spills by month, utility volume, and volume buckets.
   * Table should show `Showing X of Y records (limit Z)` and rows matching the filter.
