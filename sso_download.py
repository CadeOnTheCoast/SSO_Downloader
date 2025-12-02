"""CLI entrypoint for downloading ADEM SSO records to CSV."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from typing import Iterable

from sso_analytics import QAIssue, run_basic_qa, summarize_overall_volume, summarize_volume_by_utility
from sso_schema import normalize_sso_records

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
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print a brief volume summary after download",
    )
    parser.add_argument(
        "--qa-report",
        action="store_true",
        help="Run basic QA checks and print findings",
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


def _print_summary(records_norm):
    overall = summarize_overall_volume(records_norm)
    print("=== Volume summary ===")
    print(
        f"Total records with volume: {overall.count}\n"
        f"Total volume (gallons): {overall.total_volume_gallons}\n"
        f"Mean volume (gallons): {overall.mean_volume_gallons}\n"
        f"Median volume (gallons): {overall.median_volume_gallons}\n"
        f"Max volume (gallons): {overall.max_volume_gallons}"
    )

    by_utility = summarize_volume_by_utility(records_norm)[:5]
    if by_utility:
        print("Top utilities by total volume:")
        for summary in by_utility:
            print(f"- {summary.group_key}: {summary.total_volume_gallons} gallons across {summary.count} spills")


def _print_qa_report(records_norm):
    issues = run_basic_qa(records_norm)
    if not issues:
        print("No QA issues detected.")
        return

    print("=== QA report ===")
    severity_counts: dict[str, int] = {}
    for issue in issues:
        severity_counts[issue.severity] = severity_counts.get(issue.severity, 0) + 1
    for severity, count in sorted(severity_counts.items(), reverse=True):
        print(f"{severity.title()}: {count}")

    issues_by_code: dict[str, list[QAIssue]] = {}
    for issue in issues:
        issues_by_code.setdefault(issue.code, []).append(issue)

    for code, code_issues in sorted(issues_by_code.items()):
        preview = code_issues[:3]
        print(f"- {code}: {len(code_issues)} occurrences")
        for issue in preview:
            sso_part = f" (SSO ID {issue.sso_id})" if issue.sso_id else ""
            print(f"    {issue.message}{sso_part}")


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
        return 0

    records_norm = normalize_sso_records(records)
    write_ssos_to_csv(records, args.output)
    _summarize(records, args.output, args.limit)
    if args.summary:
        _print_summary(records_norm)
    if args.qa_report:
        _print_qa_report(records_norm)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
