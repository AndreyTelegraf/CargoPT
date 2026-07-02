from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.domain.job_offer_status import JobOfferStatus
from app.domain.job_status import JobStatus
from app.models.carrier import CarrierVehicle
from app.models.job import JobOffer
from app.repositories.job import JobRepository


class OfferAlreadyResolvedError(ValueError):
    pass


def parse_offer_callback(data: str) -> tuple[str, int]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "offer":
        raise ValueError("invalid callback data")

    action = parts[1]
    offer_id = int(parts[2])

    if action not in {"accept", "decline"}:
        raise ValueError("invalid offer action")

    return action, offer_id


class JobAlreadyAssignedError(ValueError):
    pass


class ClientOfferSelectionError(ValueError):
    pass


class JobOfferService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def create_offer(
        self,
        *,
        job_id: int,
        vehicle: CarrierVehicle,
        expires_in_minutes: int = 60,
    ) -> JobOffer:
        now = datetime.now(UTC)

        offer = JobOffer(
            job_id=job_id,
            carrier_id=vehicle.carrier_id,
            vehicle_id=vehicle.id,
            status=JobOfferStatus.PENDING,
            offered_at=now,
            responded_at=None,
            expires_at=now + timedelta(minutes=expires_in_minutes),
            carrier_note=None,
            price_cents=None,
            carrier_message_chat_id=None,
            carrier_message_id=None,
            created_at=now,
            updated_at=now,
        )

        return await self.repository.create_offer(offer)

    async def accept_offer(
        self,
        offer_id: int,
    ) -> JobOffer:
        now = datetime.now(UTC)
        return await self.repository.update_offer_status(
            offer_id=offer_id,
            status=JobOfferStatus.ACCEPTED,
            responded_at=now,
        )

    async def accept_offer_without_assignment(
        self,
        offer_id: int,
    ) -> JobOffer:
        now = datetime.now(UTC)

        offer = await self.repository.get_offer_by_id(offer_id)

        if offer is None:
            raise ValueError("offer not found")

        if offer.status != JobOfferStatus.PENDING:
            raise OfferAlreadyResolvedError("offer already resolved")

        job = await self.repository.get_job_by_id(offer.job_id)

        if job is None:
            raise ValueError("job not found")

        if job.status not in {
            JobStatus.MATCHING,
            JobStatus.OFFERED,
        }:
            raise JobAlreadyAssignedError("job is not accepting offers")

        offer.status = JobOfferStatus.ACCEPTED
        offer.responded_at = now
        offer.updated_at = now

        await self.repository.update_job_status(
            job_id=offer.job_id,
            status=JobStatus.OFFERED,
            updated_at=now,
        )

        return offer

    async def decline_offer(
        self,
        offer_id: int,
        decline_reason: str | None = None,
    ) -> JobOffer:
        now = datetime.now(UTC)
        return await self.repository.update_offer_status(
            offer_id=offer_id,
            status=JobOfferStatus.DECLINED,
            responded_at=now,
            decline_reason=decline_reason,
        )

    async def select_accepted_offer_for_client(
        self,
        *,
        job_id: int,
        offer_id: int,
    ) -> JobOffer:
        now = datetime.now(UTC)

        offer = await self.repository.get_offer_by_id(offer_id)

        if offer is None:
            raise ClientOfferSelectionError("offer not found")

        if offer.job_id != job_id:
            raise ClientOfferSelectionError("offer does not belong to job")

        if offer.status != JobOfferStatus.ACCEPTED:
            raise ClientOfferSelectionError("offer is not accepted by carrier")

        job = await self.repository.get_job_by_id(job_id)

        if job is None:
            raise ClientOfferSelectionError("job not found")

        if job.status != JobStatus.OFFERED:
            raise ClientOfferSelectionError("job is not awaiting client offer selection")

        await self.repository.update_job_status(
            job_id=job_id,
            status=JobStatus.ASSIGNED_PENDING_CONFIRMATION,
            updated_at=now,
        )

        await self.repository.close_unselected_offers_by_job_except(
            job_id=job_id,
            selected_offer_id=offer.id,
            responded_at=now,
        )

        return offer

    async def accept_offer_and_assign_job(
        self,
        offer_id: int,
    ) -> JobOffer:
        now = datetime.now(UTC)

        offer = await self.repository.get_offer_by_id(offer_id)

        if offer is None:
            raise ValueError("offer not found")

        if offer.status != JobOfferStatus.PENDING:
            raise OfferAlreadyResolvedError("offer already resolved")

        job = await self.repository.get_job_by_id(offer.job_id)

        if job is None:
            raise ValueError("job not found")

        if job.status not in {
            JobStatus.MATCHING,
            JobStatus.OFFERED,
        }:
            raise JobAlreadyAssignedError("job is not accepting offers")

        offer.status = JobOfferStatus.ACCEPTED
        offer.responded_at = now
        offer.updated_at = now

        await self.repository.update_job_status(
            job_id=offer.job_id,
            status=JobStatus.ASSIGNED_PENDING_CONFIRMATION,
            updated_at=now,
        )

        await self.repository.decline_pending_offers_by_job_except(
            job_id=offer.job_id,
            accepted_offer_id=offer.id,
            responded_at=now,
        )

        return offer
