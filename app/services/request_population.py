from dataclasses import dataclass

from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService


@dataclass(frozen=True)
class RequestPopulationAddress:
    kind: str
    raw_text: str
    floor: int | None = None
    has_elevator: bool | None = None
    normalized_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class RequestPopulationItem:
    description: str
    quantity: int | None = None


class RequestPopulationService:
    def __init__(self, *, job_repository: JobRepository) -> None:
        self.job_repository = job_repository

    async def populate(
        self,
        *,
        job_id: int,
        addresses: tuple[RequestPopulationAddress, ...],
        items: tuple[RequestPopulationItem, ...],
    ) -> None:
        update_service = RequestUpdateService(job_repository=self.job_repository)

        for address_payload in addresses:
            address = await update_service.add_address(
                job_id=job_id,
                kind=address_payload.kind,
                raw_text=address_payload.raw_text,
                normalized_address=address_payload.normalized_address,
                latitude=address_payload.latitude,
                longitude=address_payload.longitude,
            )
            if address_payload.floor is not None or address_payload.has_elevator is not None:
                await update_service.update_address_details(
                    address_id=address.id,
                    floor=address_payload.floor,
                    has_elevator=address_payload.has_elevator,
                )

        for item_payload in items:
            await update_service.add_item(
                job_id=job_id,
                description=item_payload.description,
                quantity=item_payload.quantity,
            )
