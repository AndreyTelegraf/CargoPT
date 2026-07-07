from dataclasses import dataclass
from enum import StrEnum

from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.services.carrier_search import CarrierSearchService
from app.services.location_normalization import geocode_text_address


REGION_KEYWORDS = {
    "Lisboa": [
        "lisboa",
        "alcochete",
        "cascais",
        "sintra",
        "oeiras",
        "amadora",
        "loures",
        "odivelas",
        "mafra",
        "vila franca de xira",
        "setúbal",
        "setubal",
        "almada",
        "seixal",
        "barreiro",
        "moita",
        "montijo",
        "palmela",
        "sesimbra",
    ],
    "Porto": [
        "porto",
        "vila nova de gaia",
        "gaia",
        "matosinhos",
        "maia",
        "gondomar",
        "valongo",
        "póvoa de varzim",
        "povoa de varzim",
        "vila do conde",
    ],
    "Centro": [
        "centro",
        "aveiro",
        "coimbra",
        "leiria",
        "marinha grande",
        "viseu",
        "castelo branco",
        "guarda",
    ],
    "Alentejo": [
        "alentejo",
        "évora",
        "evora",
        "beja",
        "portalegre",
        "santarém",
        "santarem",
    ],
    "Algarve": [
        "algarve",
        "faro",
        "loulé",
        "loule",
        "albufeira",
        "portimão",
        "portimao",
        "lagos",
        "tavira",
        "olhão",
        "olhao",
    ],
}


REGION_BOUNDING_BOXES = [
    (
        "Lisboa",
        {
            "lat_min": 38.25,
            "lat_max": 39.25,
            "lon_min": -9.65,
            "lon_max": -8.45,
        },
    ),
    (
        "Porto",
        {
            "lat_min": 40.80,
            "lat_max": 41.65,
            "lon_min": -8.95,
            "lon_max": -7.75,
        },
    ),
    (
        "Algarve",
        {
            "lat_min": 36.80,
            "lat_max": 37.60,
            "lon_min": -9.10,
            "lon_max": -7.20,
        },
    ),
    (
        "Centro",
        {
            "lat_min": 39.20,
            "lat_max": 41.35,
            "lon_min": -9.40,
            "lon_max": -6.70,
        },
    ),
    (
        "Alentejo",
        {
            "lat_min": 37.25,
            "lat_max": 39.75,
            "lon_min": -9.20,
            "lon_max": -6.80,
        },
    ),
]


def _regions_from_text(value: str | None) -> set[str]:
    if not value:
        return set()

    normalized = value.casefold()
    regions = set()

    for region, keywords in REGION_KEYWORDS.items():
        if any(keyword.casefold() in normalized for keyword in keywords):
            regions.add(region)

    return regions


def _regions_from_coordinates(
    latitude: float | None,
    longitude: float | None,
) -> set[str]:
    if latitude is None or longitude is None:
        return set()

    for region, bounds in REGION_BOUNDING_BOXES:
        if (
            bounds["lat_min"] <= latitude <= bounds["lat_max"]
            and bounds["lon_min"] <= longitude <= bounds["lon_max"]
        ):
            return {region}

    return set()


def _address_text_candidates(address) -> list[str]:
    candidates = []

    for value in (address.normalized_address, address.raw_text):
        if not isinstance(value, str):
            continue

        value = value.strip()
        if not value:
            continue

        if "consent.google.com" in value:
            continue

        if value not in candidates:
            candidates.append(value)

    return candidates


async def _regions_from_geocoded_address(address) -> set[str]:
    for candidate in _address_text_candidates(address):
        latitude, longitude = await geocode_text_address(candidate)
        regions = _regions_from_coordinates(latitude, longitude)

        if regions:
            return regions

    return set()


class MatchingReason(StrEnum):
    MATCH_FOUND = "match_found"
    NO_ADDRESSES = "no_addresses"
    REGION_FROM_COORDINATES = "region_from_coordinates"
    REGION_FROM_GEOCODING = "region_from_geocoding"
    REGION_FROM_TEXT_FALLBACK = "region_from_text_fallback"
    REGION_NOT_DETERMINED = "region_not_determined"
    NO_ELIGIBLE_CARRIERS = "no_eligible_carriers"


@dataclass(frozen=True)
class MatchingResult:
    vehicles: list[CarrierVehicle]
    reason: MatchingReason
    regions: list[str]


class JobMatchingService:
    def __init__(self, carrier_search: CarrierSearchService) -> None:
        self.carrier_search = carrier_search

    async def find_matching_result_for_job(
        self,
        job: Job,
        addresses=None,
    ) -> MatchingResult:
        regions = set()
        reason = MatchingReason.NO_ADDRESSES
        loaded_addresses = addresses
        if loaded_addresses is None:
            loaded_addresses = getattr(job, "__dict__", {}).get("addresses") or []

        for address in loaded_addresses:
            regions.update(
                _regions_from_coordinates(
                    address.latitude,
                    address.longitude,
                )
            )

        if regions:
            reason = MatchingReason.REGION_FROM_COORDINATES

        if loaded_addresses and not regions:
            for address in loaded_addresses:
                regions.update(await _regions_from_geocoded_address(address))

            if regions:
                reason = MatchingReason.REGION_FROM_GEOCODING

        if loaded_addresses and not regions:
            for address in loaded_addresses:
                regions.update(_regions_from_text(address.raw_text))
                regions.update(_regions_from_text(address.normalized_address))

            if regions:
                reason = MatchingReason.REGION_FROM_TEXT_FALLBACK

        if loaded_addresses and not regions:
            return MatchingResult(
                vehicles=[],
                reason=MatchingReason.REGION_NOT_DETERMINED,
                regions=[],
            )

        vehicles = await self.carrier_search.find_matching_vehicles(
            min_payload_kg=None,
            min_volume_m3=None,
            min_loaders=None,
            needs_tail_lift=job.needs_tail_lift,
            needs_crane=job.needs_crane,
            needs_mobile_lift=job.needs_mobile_lift,
            needs_assembly=job.needs_assembly,
            needs_packing=job.needs_packing,
            regions=sorted(regions) or None,
        )

        if not vehicles:
            return MatchingResult(
                vehicles=[],
                reason=MatchingReason.NO_ELIGIBLE_CARRIERS,
                regions=sorted(regions),
            )

        return MatchingResult(
            vehicles=vehicles,
            reason=MatchingReason.MATCH_FOUND,
            regions=sorted(regions),
        )

    async def find_matching_vehicles_for_job(
        self,
        job: Job,
        addresses=None,
    ) -> list[CarrierVehicle]:
        result = await self.find_matching_result_for_job(
            job,
            addresses=addresses,
        )
        return result.vehicles
