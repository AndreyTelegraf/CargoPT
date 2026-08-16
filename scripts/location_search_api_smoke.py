import os
from pathlib import Path

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from fastapi.testclient import TestClient

from app.api.main import app
from app.api import web_requests
from app.services.location_normalization import LocationSuggestion


ROOT = Path(__file__).resolve().parents[1]


async def fake_search(
    query: str,
    *,
    locale: str,
    limit: int,
    provider_url: str,
):
    assert query == "Carvoeiro"
    assert locale == "ru"
    assert limit == 5
    assert provider_url == "https://nominatim.openstreetmap.org/search"
    return [
        LocationSuggestion(
            display_name="Carvoeiro, Lagoa, Faro, Portugal",
            latitude=37.0970567,
            longitude=-8.4711093,
            map_url=(
                "https://www.google.com/maps/search/"
                "?api=1&query=37.0970567,-8.4711093"
            ),
        ),
        LocationSuggestion(
            display_name="Carvoeiro, Viana do Castelo, Portugal",
            latitude=41.6509991,
            longitude=-8.6636379,
            map_url=(
                "https://www.google.com/maps/search/"
                "?api=1&query=41.6509991,-8.6636379"
            ),
        ),
    ]


def main() -> None:
    original = web_requests.search_location_suggestions
    web_requests.search_location_suggestions = fake_search
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/locations/search",
                params={"q": "Carvoeiro", "locale": "ru", "limit": 5},
            )
            short_query = client.get(
                "/api/v1/locations/search",
                params={"q": "Ca", "locale": "ru"},
            )
    finally:
        web_requests.search_location_suggestions = original

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 2
    assert body[0]["display_name"] == "Carvoeiro, Lagoa, Faro, Portugal"
    assert body[0]["latitude"] == 37.0970567
    assert body[0]["country_code"] == "pt"
    assert body[1]["latitude"] == 41.6509991
    assert short_query.status_code == 422

    normalization_source = (
        ROOT / "app/services/location_normalization.py"
    ).read_text(encoding="utf-8")
    assert "NOMINATIM_MIN_INTERVAL_SECONDS = 1.05" in normalization_source
    assert "NOMINATIM_CACHE_TTL_SECONDS = 86400" in normalization_source
    assert "await asyncio.sleep(wait_seconds)" in normalization_source
    assert "contact: hello@cargopt.pt" in normalization_source

    config_source = (ROOT / "app/config.py").read_text(encoding="utf-8")
    assert "location_search_provider_url:" in config_source

    print("LOCATION_SEARCH_API_SMOKE_OK")


if __name__ == "__main__":
    main()
