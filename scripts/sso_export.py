"""CSV export helpers for SSO records."""
from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import IO, Iterable, List, Sequence


def _determine_fieldnames(records: Sequence[dict]) -> List[str]:
    keys = set()
    for record in records:
        keys.update(record.keys())
    return sorted(keys)


def _write_records_to_handle(records: List[dict], handle: IO[str]) -> None:
    fieldnames = _determine_fieldnames(records)
    if not fieldnames:
        handle.write("")
        return

    writer = csv.DictWriter(handle, fieldnames=fieldnames)
    writer.writeheader()
    for row in records:
        writer.writerow(row)


def write_ssos_to_csv_filelike(records: Iterable[dict], handle: IO[str]) -> None:
    """Write SSO records to a CSV file-like object.

    This helper mirrors :func:`write_ssos_to_csv` but targets an existing
    text handle, enabling in-memory CSV generation for HTTP responses or
    other non-filesystem outputs.
    """

    records_list = list(records)
    _write_records_to_handle(records_list, handle)


def write_ssos_to_csv(records: Iterable[dict], output_path: str) -> None:
    records_list = list(records)

    path = Path(output_path)
    open_fn = gzip.open if path.suffix == ".gz" else open
    with open_fn(path, "wt", encoding="utf-8", newline="") as csvfile:
        _write_records_to_handle(records_list, csvfile)
