import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.location_normalization import build_google_maps_coordinate_url
from app.services.location_normalization import normalize_text_location

location = normalize_text_location("Rua Augusta 1, Lisboa 1100-048")
assert location["normalized_address"] == "Rua Augusta 1, Lisboa 1100-048"
assert location["postal_code"] == "1100-048"
assert location["map_url"].startswith("https://www.google.com/maps/search/?api=1&query=")
assert "Rua+Augusta" in location["map_url"]

location = normalize_text_location("https://maps.app.goo.gl/test123")
assert location["original_google_maps_url"] == "https://maps.app.goo.gl/test123"
assert location["map_url"] == "https://maps.app.goo.gl/test123"

assert build_google_maps_coordinate_url(38.7223, -9.1393).endswith("38.7223,-9.1393")

print("JOB_LOCATION_NORMALIZATION_SMOKE_OK")
