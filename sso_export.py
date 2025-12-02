"""CSV export helpers for SSO records."""
from __future__ import annotations

import csv
import gzip
from pathlib import Path
from typing import Iterable, List, Sequence


def _determine_fieldnames(records: Sequence[dict]) -> List[str]:
    keys = set()
    for record in records:
        keys.update(record.keys())
    return sorted(keys)


def write_ssos_to_csv(records: Iterable[dict], output_path: str) -> None:
    records_list = list(records)
    fieldnames = _determine_fieldnames(records_list)

    path = Path(output_path)
    open_fn = gzip.open if path.suffix == ".gz" else open
    with open_fn(path, "wt", encoding="utf-8", newline="") as csvfile:
        if not fieldnames:
            csvfile.write("")
            return

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in records_list:
            writer.writerow(row)
