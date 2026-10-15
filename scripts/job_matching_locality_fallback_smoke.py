import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.services import job_matching as matching


def address(raw, normalized=None, latitude=None, longitude=None):
    return SimpleNamespace(raw_text=raw, normalized_address=normalized or raw,
                           country_code="pt", latitude=latitude, longitude=longitude)


async def main():
    destination = address("Praceta F1 T1\nhttps://maps.app.goo.gl/ccsGX6WxGj8foe7p7",
                          "Praceta F1 T1, Santo António dos Cavaleiros")
    assert matching._address_locality_candidates(destination) == ["Santo António dos Cavaleiros"]
    for ambiguous in ("Praceta F1 T1", "Rua Teste, 2D", "Rua Teste, Portugal",
                      "Rua Teste, Avenida Teste", "https://maps.google.com/?q=1,2"):
        assert matching._address_locality_candidates(address(ambiguous)) == []

    async def geocode(query):
        return (38.812632, -9.1613378) if query == "Santo António dos Cavaleiros" else (None, None)

    job = SimpleNamespace(estimated_payload_kg=None, estimated_volume_m3=None,
                          required_loaders=None, needs_tail_lift=False, needs_crane=False,
                          needs_mobile_lift=False, needs_assembly=False, needs_packing=False)
    search = SimpleNamespace(find_matching_vehicles=AsyncMock(return_value=[SimpleNamespace(id=1)]))
    service = matching.JobMatchingService(search)
    pickup = address("Lisbon Rua Maluda 25 -2d", latitude=38.790447, longitude=-9.1507413)
    with patch.object(matching, "geocode_text_address", AsyncMock(side_effect=geocode)) as geocoder:
        result = await service.find_matching_result_for_job(job, addresses=[pickup, destination])
        assert result.reason == matching.MatchingReason.MATCH_FOUND
        assert result.regions == ["Lisboa"]
        assert search.find_matching_vehicles.call_args.kwargs["regions"] == ["Lisboa"]
        assert any(call.args == ("Santo António dos Cavaleiros",) for call in geocoder.await_args_list)
        assert destination.latitude is None and destination.longitude is None

    search.find_matching_vehicles.reset_mock()
    with patch.object(matching, "geocode_text_address", AsyncMock(return_value=(None, None))):
        result = await service.find_matching_result_for_job(job, addresses=[pickup, address("Rua Teste, Local Desconhecido")])
        assert result.reason == matching.MatchingReason.REGION_NOT_DETERMINED
        search.find_matching_vehicles.assert_not_awaited()

    with patch.object(matching, "geocode_text_address", AsyncMock()) as geocoder:
        result = await service.find_matching_result_for_job(job, addresses=[pickup])
        assert result.regions == ["Lisboa"]
        geocoder.assert_not_awaited()
    print("JOB_MATCHING_LOCALITY_FALLBACK_SMOKE_OK")


asyncio.run(main())
