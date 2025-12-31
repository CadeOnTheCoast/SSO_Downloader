import pytest
from sso_analytics import classify_sso_cause

def test_classify_sso_cause_heavy_rain():
    assert classify_sso_cause("Heavy rain and inflow") == "Heavy Rain"
    assert classify_sso_cause("Storm event") == "Heavy Rain"
    assert classify_sso_cause("I/I during wet weather") == "Heavy Rain"
    assert classify_sso_cause("overflow due to rain") == "Heavy Rain"

def test_classify_sso_cause_power_failure():
    assert classify_sso_cause("Power outage at lift station") == "Power Failure"
    assert classify_sso_cause("Electrical failure") == "Power Failure"
    assert classify_sso_cause("Utility power loss") == "Power Failure"

def test_classify_sso_cause_infrastructure_failure():
    assert classify_sso_cause("Broken main") == "Infrastructure Failure"
    assert classify_sso_cause("Grease blockage") == "Infrastructure Failure"
    assert classify_sso_cause("Tree roots") == "Infrastructure Failure"
    assert classify_sso_cause("Crack in pipe") == "Infrastructure Failure"
    assert classify_sso_cause("plugged gravity main") == "Infrastructure Failure"

def test_classify_sso_cause_lift_station_failure():
    assert classify_sso_cause("Lift station pump failed") == "Lift Station Failure"
    assert classify_sso_cause("LS overflow") == "Lift Station Failure"
    assert classify_sso_cause("Float failure at pump station") == "Lift Station Failure"

def test_classify_sso_cause_treatment_plant_failure():
    assert classify_sso_cause("WWTP clarifier overflow") == "Treatment Plant Failure"
    assert classify_sso_cause("Treatment plant headworks failure") == "Treatment Plant Failure"

def test_classify_sso_cause_development_damage():
    assert classify_sso_cause("Line cut by contractor") == "Development Damage"
    assert classify_sso_cause("Construction damage") == "Development Damage"
    assert classify_sso_cause("Third party excavation") == "Development Damage"

def test_classify_sso_cause_unknown_other():
    assert classify_sso_cause(None) == "Unknown"
    assert classify_sso_cause("") == "Unknown"
    assert classify_sso_cause("Vandalism") == "Other"
    assert classify_sso_cause("Unknown") == "Other" # 'Unknown' string is classified as 'Other' currently
