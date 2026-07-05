import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

import app.services.location_normalization as location_normalization


async def fake_geocode_text_address(address: str):
    if address != "Rua Augusta 1, 1100-048 Lisboa":
        raise AssertionError(address)
    return 38.7107, -9.1371


location_normalization.geocode_text_address = fake_geocode_text_address


async def main() -> None:
    result = await location_normalization.normalize_text_location_resolved(
        "Rua Augusta 1, 1100-048 Lisboa"
    )

    assert result["normalized_address"] == "Rua Augusta 1, 1100-048 Lisboa"
    assert result["postal_code"] == "1100-048"
    assert result["latitude"] == 38.7107
    assert result["longitude"] == -9.1371
    assert result["map_url"].endswith("38.7107,-9.1371")

    print("JOB_LOCATION_NOMINATIM_GEOCODING_SMOKE_OK")


asyncio.run(main())
