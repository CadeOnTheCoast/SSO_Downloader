import pytest
from sso_analytics import _normalize_receiving_water_name, CONTAINED_LABEL

def test_normalize_receiving_water_parentheses():
    assert _normalize_receiving_water_name("Ground Absorbed;Drainage Ditch(Coosa River)") == "Coosa River"
    assert _normalize_receiving_water_name("Drainage Ditch(Coosa River)") == "Coosa River"
    assert _normalize_receiving_water_name("Tributary (Yellow Leaf Creek)") == "Yellow Leaf Creek"

def test_normalize_receiving_water_keywords():
    assert _normalize_receiving_water_name("Guntersville Lake") == "Guntersville Lake"
    assert _normalize_receiving_water_name("Cahaba River") == "Cahaba River"
    assert _normalize_receiving_water_name("Black Warrior") == "Black Warrior" # 'water' or matching keyword needed? 
    # 'water' is in keywords. If 'Black Warrior' doesn't match, it falls back to parts[0]

def test_normalize_receiving_water_contained():
    assert _normalize_receiving_water_name("Ground Absorbed") == CONTAINED_LABEL
    assert _normalize_receiving_water_name("Backup into building") == CONTAINED_LABEL
    assert _normalize_receiving_water_name("Ground Absorbed; Backup") == CONTAINED_LABEL

def test_normalize_receiving_water_complex():
    # Prioritize keyword over non-keyword part even if later
    assert _normalize_receiving_water_name("No specific stream; Paint Rock River") == "Paint Rock River"
    # Ground absorbed should be ignored if a waterbody is found
    assert _normalize_receiving_water_name("Ground absorbed; Turkey Creek") == "Turkey Creek"

def test_normalize_receiving_water_fallback():
    assert _normalize_receiving_water_name("Some unknown location") == "Some unknown location"
    assert _normalize_receiving_water_name(None) == None
    assert _normalize_receiving_water_name("Unknown") == None
