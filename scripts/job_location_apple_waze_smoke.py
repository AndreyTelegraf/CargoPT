import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.location_normalization import extract_coordinates
from app.services.location_normalization import normalize_text_location

apple_coordinates = normalize_text_location(
    "https://maps.apple.com/?ll=38.7223,-9.1393&q=Lisboa"
)
assert apple_coordinates["latitude"] == 38.7223
assert apple_coordinates["longitude"] == -9.1393

apple_address = normalize_text_location(
    "https://maps.apple.com/?address=Rua%20Augusta%201%2C%201100-048%20Lisboa"
)
assert apple_address["normalized_address"] == "Rua Augusta 1, 1100-048 Lisboa"
assert apple_address["postal_code"] == "1100-048"

waze_coordinates = normalize_text_location(
    "https://waze.com/ul?ll=38.7223,-9.1393&navigate=yes"
)
assert waze_coordinates["latitude"] == 38.7223
assert waze_coordinates["longitude"] == -9.1393

waze_address = normalize_text_location(
    "https://waze.com/ul?q=Rua%20Augusta%201%2C%201100-048%20Lisboa"
)
assert waze_address["normalized_address"] == "Rua Augusta 1, 1100-048 Lisboa"
assert waze_address["postal_code"] == "1100-048"

assert extract_coordinates("https://maps.apple.com/?ll=38.7223,-9.1393") == (
    38.7223,
    -9.1393,
)
assert extract_coordinates("https://waze.com/ul?ll=38.7223,-9.1393") == (
    38.7223,
    -9.1393,
)

print("JOB_LOCATION_APPLE_WAZE_SMOKE_OK")
