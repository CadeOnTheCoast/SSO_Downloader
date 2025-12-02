"""CLI entrypoint for downloading ADEM SSO records to CSV."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Iterable

from sso_client import SSOClient, SSOClientError
from sso_export import write_ssos_to_csv
from sso_schema import SSOQuery


def _parse_date(value: str | None):
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date '{value}'. Expected format YYYY-MM-DD."
        ) from exc


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download ADEM SSO records to CSV")
    parser.add_argument("-o", "--output", required=True, help="Path to output CSV file")
    parser.add_argument("--utility-id", help="Filter by utility/permit ID")
    parser.add_argument("--utility-name", help="Filter by utility/permit name")
    parser.add_argument("--county", help="Filter by county (if available)")
    parser.add_argument("--start-date", type=_parse_date, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=_parse_date, help="End date (YYYY-MM-DD)")
    parser.add_argument("--min-volume", type=float, help="Minimum spill volume (gallons)")
    parser.add_argument("--max-volume", type=float, help="Maximum spill volume (gallons)")
    parser.add_argument("--limit", type=int, help="Maximum number of records to fetch")
    parser.add_argument("--base-url", help="Override the ArcGIS base URL")
    parser.add_argument("--api-key", help="API token for the ArcGIS service, if required")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument(
        "--allow-no-filters",
        action="store_true",
        help="Allow running without any filters (may request a large dataset)",
    )
    return parser


def _ensure_filters_present(args: argparse.Namespace) -> None:
    has_filter = any(
        [
            args.utility_id,
            args.utility_name,
            args.county,
            args.start_date,
            args.end_date,
            args.min_volume,
            args.max_volume,
        ]
    )
    if not has_filter and not args.allow_no_filters:
        raise SystemExit(
            "At least one filter must be provided. Add --allow-no-filters to proceed without filters."
        )


def _summarize(records: Iterable[dict], output_path: str, limit: int | None) -> None:
    count = len(list(records)) if not isinstance(records, list) else len(records)
    message_parts = [f"Fetched {count} records"]
    if limit is not None and count >= limit:
        message_parts.append("(truncated by --limit)")
    message_parts.append(f"Saved to {output_path}")
    print(" ".join(message_parts))


def main(argv: list[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    _ensure_filters_present(args)

    query = SSOQuery(
        utility_id=args.utility_id,
        utility_name=args.utility_name,
        county=args.county,
        start_date=args.start_date,
        end_date=args.end_date,
        min_volume_gallons=args.min_volume,
        max_volume_gallons=args.max_volume,
    )

    try:
        query.validate()
    except ValueError as exc:
        print(f"Invalid filters: {exc}", file=sys.stderr)
        return 2

    client = SSOClient(base_url=args.base_url, api_key=args.api_key, timeout=args.timeout)

    try:
        records = client.fetch_ssos(
            query=query,
            limit=args.limit,
        )
    except SSOClientError as exc:
        print(f"Error fetching SSO records: {exc}", file=sys.stderr)
        return 1

    if not records:
        print("No records returned for the given filters.")
    write_ssos_to_csv(records, args.output)
    _summarize(records, args.output, args.limit)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
