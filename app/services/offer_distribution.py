from app.domain.job_status import JobStatus
from app.models.job import Job
from app.models.job import JobOffer
from app.repositories.job import JobRepository
from app.services.job_matching import JobMatchingService
from app.services.job_matching import _regions_from_text
from app.services.job_offer import JobOfferService


class OfferDistributionService:
    def __init__(
        self,
        *,
        matching_service: JobMatchingService,
        offer_service: JobOfferService,
        job_repository: JobRepository,
    ) -> None:
        self.matching_service = matching_service
        self.offer_service = offer_service
        self.job_repository = job_repository

    async def create_offers_for_job(
        self,
        job: Job,
        *,
        limit: int | None = None,
        expires_in_minutes: int = 60,
    ) -> list[JobOffer]:
        await self.job_repository.update_job_status(
            job_id=job.id,
            status=JobStatus.MATCHING,
            updated_at=job.updated_at,
        )

        existing_carrier_ids = await self.job_repository.list_offer_carrier_ids_by_job(job.id)
        addresses = await self.job_repository.list_addresses_by_job(job.id)
        matched_regions = set()
        for address in addresses:
            matched_regions.update(_regions_from_text(address.raw_text))
            matched_regions.update(_regions_from_text(address.normalized_address))

        vehicles = await self.matching_service.find_matching_vehicles_for_job(
            job,
            addresses=addresses,
        )
        if not vehicles and not matched_regions:
            vehicles = []

        selected = []
        selected_carrier_ids = set(existing_carrier_ids)

        for vehicle in vehicles:
            if vehicle.carrier_id in selected_carrier_ids:
                continue

            selected.append(vehicle)
            selected_carrier_ids.add(vehicle.carrier_id)

            if limit is not None and len(selected) >= limit:
                break

        offers = []

        for vehicle in selected:
            offer = await self.offer_service.create_offer(
                job_id=job.id,
                vehicle=vehicle,
                expires_in_minutes=expires_in_minutes,
            )
            offers.append(offer)

        target_status = JobStatus.OFFERED if offers else JobStatus.NO_CARRIERS_FOUND

        await self.job_repository.update_job_status(
            job_id=job.id,
            status=target_status,
            updated_at=job.updated_at,
        )

        return offers
