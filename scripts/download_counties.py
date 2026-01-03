
import requests
import json
import os

URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
TARGET_FILE = "frontend/data/al_counties.json"

def download_and_filter():
    print(f"Downloading from {URL}...")
    try:
        resp = requests.get(URL)
        resp.raise_for_status()
        data = resp.json()
        
        print("Filtering for Alabama (FIPS 01)...")
        al_features = []
        for feature in data["features"]:
            # GeoJSON properties usually have 'STATE' or 'id' starting with state fips
            # Plotly dataset uses 'id' as FIPS code. AL is '01'
            fips = feature.get("id", "")
            if fips.startswith("01"):
                al_features.append(feature)
        
        if not al_features:
            print("Error: No Alabama counties found!")
            return
            
        al_geojson = {
            "type": "FeatureCollection",
            "features": al_features
        }
        
        os.makedirs(os.path.dirname(TARGET_FILE), exist_ok=True)
        with open(TARGET_FILE, "w") as f:
            json.dump(al_geojson, f)
            
        print(f"Success! Saved {len(al_features)} counties to {TARGET_FILE}")
        
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    download_and_filter()
