from __future__ import annotations

from datetime import datetime

from sso_analytics import (
    build_dashboard_summary,
    GroupVolumeSummary,
    QAIssue,
    SpillRecordSummary,
    summarize_by_month,
    summarize_by_utility,
    summarize_by_volume_bucket,
    summarize_overall_volume,
    summarize_top_receiving_waters,
    summarize_top_utilities,
    summarize_volume_by_county,
    summarize_volume_by_month,
    summarize_volume_by_utility,
    build_time_series,
    build_utility_pie,
    top_spills_by_volume,
    top_utilities_by_volume,
    run_basic_qa,
)
from sso_schema import SSORecord


def _record(**overrides) -> SSORecord:
    defaults = dict(
        sso_id=None,
        utility_id=None,
        utility_name=None,
        sewer_system=None,
        county=None,
        location_desc=None,
        date_sso_began=None,
        date_sso_stopped=None,
        volume_gallons=None,
        cause=None,
        receiving_water=None,
        x=None,
        y=None,
        raw={},
    )
    defaults.update(overrides)
    return SSORecord(**defaults)


def test_summarize_overall_volume_ignores_missing():
    records = [
        _record(volume_gallons=10),
        _record(volume_gallons=30),
        _record(volume_gallons=None),
        _record(volume_gallons=-5),
    ]

    summary = summarize_overall_volume(records)

    assert summary.count == 2
    assert summary.total_volume_gallons == 40
    assert summary.mean_volume_gallons == 20
    assert summary.median_volume_gallons == 20
    assert summary.max_volume_gallons == 30


def test_summarize_volume_by_utility_and_county_sorted():
    records = [
        _record(utility_name="B Utility", county="Mobile", volume_gallons=20),
        _record(utility_name="A Utility", county="Mobile", volume_gallons=10),
        _record(utility_name="C Utility", county="Baldwin", volume_gallons=20),
        _record(utility_name=None, county="Shelby", volume_gallons=100),
        _record(utility_name="", county="Shelby", volume_gallons=5),
    ]

    by_utility = summarize_volume_by_utility(records)
    assert [s.group_key for s in by_utility] == ["B Utility", "C Utility", "A Utility"]
    assert [s.total_volume_gallons for s in by_utility] == [20, 20, 10]

    by_county = summarize_volume_by_county(records)
    assert [s.group_key for s in by_county] == ["Shelby", "Mobile", "Baldwin"]
    assert [s.total_volume_gallons for s in by_county] == [105, 30, 20]


def test_summarize_volume_by_month_buckets_year_month():
    records = [
        _record(date_sso_began=datetime(2024, 1, 15), volume_gallons=10),
        _record(date_sso_began=datetime(2024, 1, 20), volume_gallons=5),
        _record(date_sso_began=datetime(2024, 2, 1), volume_gallons=7),
        _record(date_sso_began=None, volume_gallons=9),
    ]

    by_month = summarize_volume_by_month(records)

    assert [s.group_key for s in by_month] == ["2024-01", "2024-02"]
    assert [s.total_volume_gallons for s in by_month] == [15, 7]


def test_run_basic_qa_detects_expected_issues():
    records = [
        _record(
            sso_id="1",
            utility_name=None,
            date_sso_began=None,
            x=None,
            y=None,
            volume_gallons=-1,
            raw={"notes": "25,000 < gall"},
        ),
        _record(
            sso_id="2",
            utility_name="Utility",
            date_sso_began=datetime(2024, 1, 1),
            x=1.0,
            y=1.0,
            volume_gallons=0,
            raw={},
        ),
    ]

    issues = run_basic_qa(records)

    codes = [issue.code for issue in issues]
    assert "NEGATIVE_VOLUME" in codes
    assert "ZERO_VOLUME" in codes
    assert "MISSING_START_DATE" in codes
    assert "MISSING_UTILITY" in codes
    assert "MISSING_GEOMETRY" in codes
    assert "VOLUME_RANGE_TEXT" in codes


def test_top_utilities_and_spills_by_volume():
    records = [
        _record(sso_id="1", utility_name="A", county="Mobile", volume_gallons=5, location_desc="Loc1"),
        _record(sso_id="2", utility_name="B", county="Mobile", volume_gallons=15, location_desc="Loc2"),
        _record(sso_id="3", utility_name="C", county="Baldwin", volume_gallons=25, location_desc="Loc3"),
        _record(sso_id="4", utility_name="D", county="Shelby", volume_gallons=None, location_desc="Loc4"),
        _record(sso_id="5", utility_name="E", county="Shelby", volume_gallons=-5, location_desc="Loc5"),
    ]

    top_utils = top_utilities_by_volume(records, n=2)
    assert [s.group_key for s in top_utils] == ["C", "B"]
    assert [s.total_volume_gallons for s in top_utils] == [25, 15]

    top_spills = top_spills_by_volume(records, n=2)
    assert [s.sso_id for s in top_spills] == ["3", "2"]
    assert isinstance(top_spills[0], SpillRecordSummary)


def test_volume_bucket_and_dashboard_summary():
    records = [
        _record(
            sso_id="1",
            utility_id="U1",
            utility_name="Alpha",
            county="Mobile",
            date_sso_began=datetime(2024, 1, 5),
            volume_gallons=500,
            receiving_water="Bay A",
        ),
        _record(
            sso_id="2",
            utility_id="U1",
            utility_name="Alpha",
            county="Mobile",
            date_sso_began=datetime(2024, 1, 20),
            volume_gallons=5_000,
            receiving_water="Bay B",
        ),
        _record(
            sso_id="3",
            utility_id="U2",
            utility_name="Beta",
            county="Baldwin",
            date_sso_began=datetime(2024, 2, 1),
            volume_gallons=150_000,
            receiving_water="Bay A",
        ),
        _record(
            sso_id="4",
            utility_id=None,
            utility_name=None,
            county="Baldwin",
            date_sso_began=None,
            volume_gallons=None,
        ),
    ]

    by_bucket = summarize_by_volume_bucket(records)
    assert by_bucket[0]["bucket_label"].startswith("0")
    assert any(row["bucket_label"] == "unknown" for row in by_bucket)
    assert sum(row["spill_count"] for row in by_bucket) == 4

    by_month = summarize_by_month(records)
    assert [row["month"] for row in by_month] == ["2024-01", "2024-02"]
    assert by_month[0]["spill_count"] == 2

    by_utility = summarize_by_utility(records)
    assert by_utility[0]["utility_id"] == "U2"
    assert by_utility[1]["utility_id"] == "U1"

    summary = build_dashboard_summary(records)
    assert summary["summary_counts"]["total_duration_hours"] == 0.0
    assert summary["summary_counts"]["total_volume"] == summary["summary_counts"]["total_volume_gallons"]
    receiving = summary.get("by_receiving_water")
    assert receiving[0]["name"] in {"Bay A", "Bay B"}
    assert any(row["name"] for row in receiving)


def test_receiving_water_normalization_and_counts():
    records = [
        _record(receiving_water="Ground Absorbed"),
        _record(receiving_water="River A; Backup into building"),
        _record(receiving_water="Blue Creek; nearby road ditch"),
        _record(receiving_water=None),
    ]

    summary = summarize_top_receiving_waters(records)
    names = [row["receiving_water_name"] for row in summary]
    assert "Contained / did not reach state waters" in names
    assert "River A" in names
    assert "Blue Creek" in names

    summary = build_dashboard_summary(records)
    assert summary["summary_counts"]["total_records"] == 4
    assert summary["summary_counts"]["distinct_utilities"] == 0
    assert summary["summary_counts"]["distinct_receiving_waters"] == 3
    assert summary["summary_counts"]["date_range"]["min"] is None
    assert summary["summary_counts"]["total_volume_gallons"] == 0.0


def test_time_series_granularity_and_top_lists():
    records = [
        _record(
            sso_id="1",
            utility_id="U1",
            utility_name="Alpha",
            receiving_water="River A",
            date_sso_began=datetime(2021, 1, 1),
            volume_gallons=1000,
        ),
        _record(
            sso_id="2",
            utility_id="U1",
            utility_name="Alpha",
            receiving_water="River B",
            date_sso_began=datetime(2021, 3, 1),
            volume_gallons=2000,
        ),
        _record(
            sso_id="3",
            utility_id="U2",
            utility_name="Beta",
            receiving_water="River A",
            date_sso_began=datetime(2022, 1, 5),
            volume_gallons=4000,
        ),
    ]

    series = build_time_series(records)
    assert series["granularity"] == "year"
    assert [point["period_label"] for point in series["points"]] == ["2021", "2022"]

    top_utils = summarize_top_utilities(records)
    assert top_utils[0]["utility_id"] == "U2"
    assert top_utils[0]["total_volume_gallons"] == 4000

    top_receiving = summarize_top_receiving_waters(records)
    assert top_receiving[0]["receiving_water_name"] == "River A"
    pie = build_utility_pie(top_utils, total_volume=6000)
    assert round(pie[0]["percent_of_total"], 2) == 66.67


