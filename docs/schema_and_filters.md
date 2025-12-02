# SSO schema and filter helpers

Module `sso_schema.py` centralizes how the ArcGIS REST SSO records are represented and how queries are built. It is intended to be shared by the CLI, future web UI, and dashboards so filters and field names stay aligned.

## Canonical record shape

`SSORecord` is a dataclass that exposes the key SSO fields with friendly snake_case names and parsed types:

- Identity and utility: `sso_id`, `utility_id` (permit number), `utility_name`, `sewer_system`, `county`, `location_desc`
- Timing: `date_sso_began`, `date_sso_stopped` as `datetime`
- Magnitude and impact: `volume_gallons`, `cause`, `receiving_water`
- Coordinates: `x`, `y`
- `raw`: the full original record dictionary for any extra fields

Use `normalize_sso_record` to convert a single raw ArcGIS feature (attributes + geometry) to an `SSORecord`, or `normalize_sso_records` to process a collection. The helpers are defensive and return `None` for fields that cannot be parsed instead of raising.

## Shared query model

`SSOQuery` captures the supported filters: utility (ID or name), county, date range, and optional volume range. Methods:

- `validate()`: raises `ValueError` on obvious issues (start date after end date, negative or inverted volume bounds).
- `build_where_clause()`: returns an ArcGIS SQL where clause with the filters applied. Date ranges are inclusive of the end date via `< end_date + 1 day`.
- `to_query_params()`: returns a parameter dictionary (including `where` and `orderByFields`) suitable for `SSOClient.fetch_ssos`.

Future consumers should prefer constructing an `SSOQuery` and passing it to the client instead of assembling where clauses manually.
