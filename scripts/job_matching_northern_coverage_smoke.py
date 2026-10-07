import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services import job_matching as matching
from app.services import location_normalization as location


def address(lat, lon):
    return SimpleNamespace(latitude=lat, longitude=lon, country_code="pt", raw_text="https://maps.app.goo.gl/test", normalized_address="https://maps.google.com/test")


async def main():
    for country, district, expected in (("pt", "PT-16", "PT-16"), ("es", "ES-PO", None), ("pt", None, None)):
        with patch.object(location, "_nominatim_search", AsyncMock(return_value=[{"address": {"country_code": country, "ISO3166-2-lvl6": district}}])) as reverse:
            assert await location.reverse_geocode_portugal_district(41.961952, -8.720723) == expected
            assert reverse.call_args.kwargs["wrap_object"] is True
            assert reverse.call_args.kwargs["provider_url"].endswith("/reverse")
    with patch.object(location, "_nominatim_search", AsyncMock(side_effect=ValueError("provider unavailable"))):
        assert await location.reverse_geocode_portugal_district(41.961952, -8.720723) is None
    job = SimpleNamespace(estimated_payload_kg=None, estimated_volume_m3=None, required_loaders=None, needs_tail_lift=False, needs_crane=False, needs_mobile_lift=False, needs_assembly=False, needs_packing=False)
    search = SimpleNamespace(find_matching_vehicles=AsyncMock(return_value=[SimpleNamespace(id=1)]))
    service = matching.JobMatchingService(search)
    with patch.object(matching, "reverse_geocode_portugal_district", AsyncMock(return_value="PT-16")) as reverse:
        result = await service.find_matching_result_for_job(job, addresses=[address(38.6555003, -9.2370586), address(41.961952, -8.720723)])
        assert result.reason == matching.MatchingReason.MATCH_FOUND
        assert result.regions == ["Lisboa", "Porto"]
        assert search.find_matching_vehicles.call_args.kwargs["regions"] == ["Lisboa", "Porto"]
        reverse.assert_awaited_once_with(41.961952, -8.720723)
    with patch.object(matching, "reverse_geocode_portugal_district", AsyncMock(return_value=None)), patch.object(matching, "geocode_text_address", AsyncMock(return_value=(None, None))):
        result = await service.find_matching_result_for_job(job, addresses=[address(42.3, -8.6)])
        assert result.reason == matching.MatchingReason.REGION_NOT_DETERMINED
    with patch.object(matching, "reverse_geocode_portugal_district", AsyncMock(return_value="PT-04")), patch.object(matching, "geocode_text_address", AsyncMock(return_value=(41.8, -6.7))):
        plain_address = address(None, None)
        plain_address.raw_text = plain_address.normalized_address = "Bragança, Portugal"
        result = await service.find_matching_result_for_job(job, addresses=[plain_address])
        assert result.reason == matching.MatchingReason.MATCH_FOUND
        assert result.regions == ["Porto"]
    for district in ("PT-03", "PT-04", "PT-13", "PT-16", "PT-17"):
        assert matching.DISTRICT_REGIONS[district] == "Porto"
    assert "PT-20" not in matching.DISTRICT_REGIONS
    assert "PT-30" not in matching.DISTRICT_REGIONS
    print("JOB_MATCHING_NORTHERN_COVERAGE_SMOKE_OK")


asyncio.run(main())
