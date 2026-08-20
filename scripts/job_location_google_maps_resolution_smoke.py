import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.location_normalization import extract_coordinates
from app.services.location_normalization import extract_link_query_address


def assert_coordinates(value: str, expected: tuple[float, float]) -> None:
    actual = extract_coordinates(value)
    if actual != expected:
        raise AssertionError(f"expected {expected}, got {actual} for {value!r}")


assert_coordinates(
    "https://www.google.com/maps/place/Test/@38.7223,-9.1393,17z",
    (38.7223, -9.1393),
)

assert extract_link_query_address(
    "https://www.google.com/maps/place/"
    "R.+Cap.+Ramires+21,+1000-084+Lisboa/data=!4m2!3m1!1sTest"
) == "R. Cap. Ramires 21, 1000-084 Lisboa"
assert_coordinates(
    "https://www.google.com/maps/search/?api=1&query=38.7223,-9.1393",
    (38.7223, -9.1393),
)
assert_coordinates(
    "https://www.google.com/maps/place/Test/data=!3d38.7223!4d-9.1393",
    (38.7223, -9.1393),
)
assert_coordinates(
    "38.7223, -9.1393",
    (38.7223, -9.1393),
)

print("JOB_LOCATION_GOOGLE_MAPS_RESOLUTION_SMOKE_OK")
