import asyncio
import os
from pathlib import Path
from types import SimpleNamespace


os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/cargopt_dev.db")

from pydantic import ValidationError

from app.api.web_request_schemas import WebRequestPayload
from app.services import location_normalization
from app.services.job_matching import JobMatchingService


async def check_search_fallback() -> None:
    calls = []
    original = location_normalization._nominatim_search

    async def fake_search(*, provider_url, params):
        calls.append(params)
        if params["q"] == "Warszawa, Leszno 32, 89":
            return []
        return [
            {
                "display_name": "32, Leszno, Warszawa, 01-199, Polska",
                "lat": "52.2383912",
                "lon": "20.9739201",
                "address": {"country_code": "pl", "postcode": "01-199"},
            }
        ]

    location_normalization._nominatim_search = fake_search
    try:
        suggestions = await location_normalization.search_location_suggestions(
            "Warszawa, Leszno 32, 89",
            locale="ru",
        )
    finally:
        location_normalization._nominatim_search = original

    assert [call["q"] for call in calls] == [
        "Warszawa, Leszno 32, 89",
        "Warszawa, Leszno 32",
    ]
    assert all("countrycodes" not in call for call in calls)
    assert len(suggestions) == 1
    assert suggestions[0].country_code == "pl"
    assert suggestions[0].postal_code == "01-199"
    assert suggestions[0].address_details_hint == "89"


def address(kind, country_code, latitude, longitude, text):
    return {
        "kind": kind,
        "raw_text": text,
        "normalized_address": text,
        "latitude": latitude,
        "longitude": longitude,
        "location_confirmed": True,
        "country_code": country_code,
    }


def check_api_contract() -> None:
    base = {
        "source_locale": "ru",
        "customer_email": "client@example.test",
        "addresses": [
            address("pickup", "pt", 38.72, -9.14, "Lisboa, Portugal"),
            address("dropoff", "pl", 52.2383912, 20.9739201, "Leszno 32, Warszawa, Polska"),
        ],
        "items": [{"description": "boxes"}],
    }
    payload = WebRequestPayload.model_validate(base)
    assert payload.addresses[1].country_code == "pl"

    inbound = dict(base)
    inbound["addresses"] = [
        address("pickup", "pl", 52.23, 20.97, "Warszawa, Polska"),
        address("dropoff", "pt", 38.72, -9.14, "Lisboa, Portugal"),
    ]
    payload = WebRequestPayload.model_validate(inbound)
    assert payload.addresses[0].country_code == "pl"
    assert payload.addresses[1].country_code == "pt"

    foreign_to_foreign = dict(base)
    foreign_to_foreign["addresses"] = [
        address("pickup", "pl", 52.23, 20.97, "Warszawa, Polska"),
        address("dropoff", "de", 48.76, 11.42, "Ingolstadt, Deutschland"),
    ]
    try:
        WebRequestPayload.model_validate(foreign_to_foreign)
    except ValidationError as error:
        assert "international routes must include Portugal" in str(error)
    else:
        raise AssertionError("foreign-to-foreign route was accepted")


async def check_portugal_endpoint_region_matching() -> None:
    class FakeCarrierSearch:
        def __init__(self):
            self.regions = None

        async def find_matching_vehicles(self, **kwargs):
            self.regions = kwargs["regions"]
            return [SimpleNamespace(id=1)]

    search = FakeCarrierSearch()
    job = SimpleNamespace(
        estimated_payload_kg=None,
        estimated_volume_m3=None,
        required_loaders=None,
        needs_tail_lift=False,
        needs_crane=False,
        needs_mobile_lift=False,
        needs_assembly=False,
        needs_packing=False,
    )
    outbound_addresses = [
        SimpleNamespace(
            kind="pickup",
            country_code="pt",
            latitude=38.72,
            longitude=-9.14,
            raw_text="Lisboa",
            normalized_address="Lisboa, Portugal",
        ),
        SimpleNamespace(
            kind="dropoff",
            country_code="pl",
            latitude=52.2383912,
            longitude=20.9739201,
            raw_text="Warszawa, Leszno 32, 89",
            normalized_address="Leszno 32, Warszawa, Polska",
        ),
    ]
    result = await JobMatchingService(search).find_matching_result_for_job(
        job,
        addresses=outbound_addresses,
    )
    assert len(result.vehicles) == 1
    assert result.regions == ["Lisboa"]
    assert search.regions == ["Lisboa"]

    inbound_search = FakeCarrierSearch()
    inbound_addresses = [
        SimpleNamespace(
            kind="pickup",
            country_code="de",
            latitude=48.76,
            longitude=11.42,
            raw_text="Ingolstadt",
            normalized_address="Ingolstadt, Deutschland",
        ),
        SimpleNamespace(
            kind="dropoff",
            country_code="pt",
            latitude=40.15,
            longitude=-8.86,
            raw_text="Figueira da Foz",
            normalized_address="Figueira da Foz, Portugal",
        ),
    ]
    result = await JobMatchingService(inbound_search).find_matching_result_for_job(
        job,
        addresses=inbound_addresses,
    )
    assert len(result.vehicles) == 1
    assert result.regions == ["Centro"]
    assert inbound_search.regions == ["Centro"]


async def main() -> None:
    await check_search_fallback()
    check_api_contract()
    await check_portugal_endpoint_region_matching()
    print("INTERNATIONAL_ADDRESS_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
