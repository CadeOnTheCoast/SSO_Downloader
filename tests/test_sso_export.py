from __future__ import annotations

import csv
import gzip
from pathlib import Path

from sso_export import write_ssos_to_csv


def test_write_ssos_to_csv_creates_expected_headers(tmp_path: Path):
    output = tmp_path / "ssos.csv"
    records = [
        {"b": "two", "a": 1},
        {"c": 3},
    ]

    write_ssos_to_csv(records, str(output))

    with output.open(newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        assert reader.fieldnames == ["a", "b", "c"]
        rows = list(reader)
        assert rows[0]["a"] == "1"
        assert rows[0]["b"] == "two"
        assert rows[1]["c"] == "3"


def test_write_ssos_to_gzip(tmp_path: Path):
    output = tmp_path / "ssos.csv.gz"
    records = [{"a": 1}]

    write_ssos_to_csv(records, str(output))

    with gzip.open(output, "rt", encoding="utf-8", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        assert reader.fieldnames == ["a"]
        assert rows[0]["a"] == "1"


def test_write_ssos_to_csv_handles_empty(tmp_path: Path):
    output = tmp_path / "empty.csv"

    write_ssos_to_csv([], str(output))

    assert output.read_text(encoding="utf-8") == ""
