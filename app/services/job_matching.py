from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.services.carrier_search import CarrierSearchService


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


def _regions_from_text(value: str | None) -> set[str]:
    if not value:
        return set()

    normalized = value.casefold()
    regions = set()

    for region, keywords in REGION_KEYWORDS.items():
        if any(keyword.casefold() in normalized for keyword in keywords):
            regions.add(region)

    return regions


class JobMatchingService:
    def __init__(self, carrier_search: CarrierSearchService) -> None:
        self.carrier_search = carrier_search

    async def find_matching_vehicles_for_job(
        self,
        job: Job,
        addresses=None,
    ) -> list[CarrierVehicle]:
        regions = set()
        loaded_addresses = addresses
        if loaded_addresses is None:
            loaded_addresses = getattr(job, "__dict__", {}).get("addresses") or []

        for address in loaded_addresses:
            regions.update(_regions_from_text(address.raw_text))
            regions.update(_regions_from_text(address.normalized_address))

        if loaded_addresses and not regions:
            return []

        return await self.carrier_search.find_matching_vehicles(
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
