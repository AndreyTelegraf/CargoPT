from app.models.carrier import CarrierVehicle
from app.repositories.carrier import CarrierRepository


class CarrierSearchService:
    def __init__(self, repository: CarrierRepository) -> None:
        self.repository = repository

    async def find_matching_vehicles(
        self,
        *,
        min_payload_kg: int | None = None,
        min_volume_m3: float | None = None,
        min_loaders: int | None = None,
        needs_tail_lift: bool = False,
        needs_crane: bool = False,
        needs_mobile_lift: bool = False,
        needs_assembly: bool = False,
        needs_packing: bool = False,
        regions: list[str] | None = None,
        requested_volume_m3: float | None = None,
        requested_loaders: int | None = None,
    ) -> list[CarrierVehicle]:
        return await self.repository.search_available_vehicles(
            min_payload_kg=min_payload_kg,
            min_volume_m3=min_volume_m3,
            min_loaders=min_loaders,
            needs_tail_lift=needs_tail_lift,
            needs_crane=needs_crane,
            needs_mobile_lift=needs_mobile_lift,
            needs_assembly=needs_assembly,
            needs_packing=needs_packing,
            regions=regions,
            requested_volume_m3=requested_volume_m3,
            requested_loaders=requested_loaders,
        )
