from dataclasses import dataclass

from app.domain.job_offer_status import JobOfferStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository


@dataclass(frozen=True)
class ClientOfferView:
    offer_id: int
    job_id: int
    carrier_id: int
    vehicle_id: int
    company_name: str
    contact_name: str | None
    phone: str | None
    telegram_username: str | None
    vehicle_type: str
    payload_kg: int | None
    volume_m3: float | None
    max_loaders: int | None
    has_tail_lift: bool
    has_crane: bool
    has_mobile_lift: bool
    carrier_note: str | None
    price_cents: int | None
    operating_regions: str | None = None
    experience_since_year: int | None = None
    logo_file_name: str | None = None


class ClientOfferPresentationService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        carrier_repository: CarrierRepository,
    ) -> None:
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository

    async def list_accepted_offer_views(self, job_id: int) -> list[ClientOfferView]:
        offers = await self.job_repository.list_offers_by_job(job_id)
        accepted_offers = [
            offer for offer in offers
            if offer.status == JobOfferStatus.ACCEPTED
        ]

        views: list[ClientOfferView] = []

        for offer in accepted_offers:
            carrier = await self.carrier_repository.get_carrier_by_id(offer.carrier_id)
            vehicle = await self.carrier_repository.get_vehicle_by_id(offer.vehicle_id)

            if carrier is None or vehicle is None:
                continue

            views.append(
                ClientOfferView(
                    offer_id=offer.id,
                    job_id=offer.job_id,
                    carrier_id=offer.carrier_id,
                    vehicle_id=offer.vehicle_id,
                    company_name=(
                        carrier.public_name
                        if carrier.publication_consent_at and carrier.public_name
                        else carrier.company_name
                    ),
                    operating_regions=(
                        carrier.operating_regions
                        if carrier.publication_consent_at
                        else None
                    ),
                    experience_since_year=(
                        carrier.experience_since_year
                        if carrier.publication_consent_at
                        else None
                    ),
                    logo_file_name=(
                        carrier.logo_file_name
                        if carrier.publication_consent_at
                        else None
                    ),
                    contact_name=carrier.contact_name,
                    phone=carrier.phone,
                    telegram_username=carrier.telegram_username,
                    vehicle_type=vehicle.vehicle_type,
                    payload_kg=vehicle.payload_kg,
                    volume_m3=vehicle.volume_m3,
                    max_loaders=vehicle.max_loaders,
                    has_tail_lift=vehicle.has_tail_lift,
                    has_crane=vehicle.has_crane,
                    has_mobile_lift=vehicle.has_mobile_lift,
                    carrier_note=offer.carrier_note,
                    price_cents=offer.price_cents,
                )
            )

        return views
