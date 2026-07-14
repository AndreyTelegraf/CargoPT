from datetime import UTC
from datetime import datetime
import secrets

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job import ClientBan
from app.models.job import Job
from app.models.job import JobAddress
from app.models.job import JobItem
from app.models.job import JobMedia
from app.models.job import JobOffer
from app.models.job import JobStatusEvent


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_client_ban(
        self,
        telegram_user_id: int,
    ) -> ClientBan | None:
        stmt = (
            select(ClientBan)
            .where(ClientBan.telegram_user_id == telegram_user_id)
            .where(ClientBan.unbanned_at.is_(None))
            .order_by(ClientBan.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def ban_client(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        reason: str | None,
        banned_by_admin_id: int,
    ) -> ClientBan:
        existing = await self.get_active_client_ban(telegram_user_id)
        if existing is not None:
            return existing

        ban = ClientBan(
            telegram_user_id=telegram_user_id,
            username=username,
            reason=reason,
            banned_by_admin_id=banned_by_admin_id,
            banned_at=datetime.now(UTC),
            unbanned_at=None,
            unbanned_by_admin_id=None,
        )
        self.session.add(ban)
        await self.session.flush()
        return ban

    async def unban_client(
        self,
        *,
        telegram_user_id: int,
        unbanned_by_admin_id: int,
    ) -> ClientBan | None:
        ban = await self.get_active_client_ban(telegram_user_id)
        if ban is None:
            return None

        ban.unbanned_at = datetime.now(UTC)
        ban.unbanned_by_admin_id = unbanned_by_admin_id
        await self.session.flush()
        return ban

    async def get_latest_job_by_client_username(
        self,
        username: str,
    ) -> Job | None:
        cleaned = username.strip().lstrip("@").lower()
        if not cleaned:
            return None

        stmt = (
            select(Job)
            .where(Job.client_telegram_username.is_not(None))
            .where(func.lower(Job.client_telegram_username) == cleaned)
            .order_by(Job.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def _generate_tracking_token(self) -> str:
        for _ in range(10):
            token = secrets.token_urlsafe(32)
            stmt = select(Job.id).where(Job.tracking_token == token).limit(1)
            result = await self.session.execute(stmt)
            if result.scalar_one_or_none() is None:
                return token

        raise RuntimeError("failed to generate unique tracking token")

    async def create_job(self, job: Job) -> Job:
        if job.tracking_token is None:
            job.tracking_token = await self._generate_tracking_token()

        self.session.add(job)
        await self.session.flush()

        initial_status = getattr(job.status, "value", job.status)
        self.session.add(
            JobStatusEvent(
                job_id=job.id,
                from_status=None,
                to_status=initial_status,
                occurred_at=job.created_at,
            )
        )

        await self.session.flush()
        return job

    async def get_job_by_id(self, job_id: int) -> Job | None:
        stmt = select(Job).where(Job.id == job_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_job_by_tracking_token(self, tracking_token: str) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.addresses))
            .where(Job.tracking_token == tracking_token)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_draft_job_by_client_id(
        self,
        telegram_user_id: int,
    ) -> Job | None:
        stmt = (
            select(Job)
            .where(Job.client_telegram_user_id == telegram_user_id)
            .where(Job.status == "draft")
            .order_by(Job.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def count_active_client_jobs(
        self,
        telegram_user_id: int,
    ) -> int:
        stmt = (
            select(func.count(Job.id))
            .where(Job.client_telegram_user_id == telegram_user_id)
            .where(
                Job.status.in_(
                    (
                        "ready_for_matching",
                        "matching",
                        "offered",
                        "assigned_pending_confirmation",
                    )
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_sent_client_jobs_since(
        self,
        telegram_user_id: int,
        since,
    ) -> int:
        stmt = (
            select(func.count(Job.id))
            .where(Job.client_telegram_user_id == telegram_user_id)
            .where(Job.updated_at >= since)
            .where(
                Job.status.in_(
                    (
                        "ready_for_matching",
                        "matching",
                        "offered",
                        "assigned_pending_confirmation",
                        "assigned",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "offers_exhausted",
                        "expired_without_response",
                        "manual_review_required",
                    )
                )
            )
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_recent_jobs(self, limit: int = 20) -> list[Job]:
        stmt = select(Job).order_by(Job.id.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_stale_assigned_pending_confirmation_jobs(
        self,
        *,
        cutoff,
        limit: int = 50,
    ) -> list[Job]:
        stmt = (
            select(Job)
            .where(Job.status == "assigned_pending_confirmation")
            .where(Job.assigned_at.is_not(None))
            .where(Job.assigned_at < cutoff)
            .order_by(Job.assigned_at, Job.id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_attention_jobs(self, limit: int = 20) -> list[Job]:
        offer_count_subquery = (
            select(func.count(JobOffer.id))
            .where(JobOffer.job_id == Job.id)
            .correlate(Job)
            .scalar_subquery()
        )

        stmt = (
            select(Job)
            .where(
                Job.status.in_(
                    (
                        "manual_review_required",
                        "no_carriers_found",
                        "offers_exhausted",
                        "expired_without_response",
                    )
                )
            )
            .order_by(
                Job.requested_date.is_(None),
                Job.requested_date,
                offer_count_subquery.desc(),
                Job.updated_at,
                Job.id,
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        jobs = list(result.scalars().all())

        if not jobs:
            return jobs

        reason_stmt = (
            select(JobOffer.job_id, JobOffer.decline_reason)
            .where(JobOffer.job_id.in_([job.id for job in jobs]))
            .where(JobOffer.decline_reason.is_not(None))
            .order_by(JobOffer.id.desc())
        )
        reason_result = await self.session.execute(reason_stmt)

        reasons_by_job_id: dict[int, str] = {}
        for job_id, decline_reason in reason_result.all():
            if job_id not in reasons_by_job_id:
                reasons_by_job_id[job_id] = decline_reason

        count_stmt = (
            select(JobOffer.job_id, func.count(JobOffer.id))
            .where(JobOffer.job_id.in_([job.id for job in jobs]))
            .group_by(JobOffer.job_id)
        )
        count_result = await self.session.execute(count_stmt)
        counts_by_job_id = {
            job_id: int(offer_count)
            for job_id, offer_count in count_result.all()
        }

        for job in jobs:
            job.attention_reason = reasons_by_job_id.get(job.id)
            job.offers_count = counts_by_job_id.get(job.id, 0)

        return jobs

    async def add_address(self, address: JobAddress) -> JobAddress:
        self.session.add(address)
        await self.session.flush()
        return address

    async def list_addresses_by_job(
        self,
        job_id: int,
    ) -> list[JobAddress]:
        stmt = (
            select(JobAddress)
            .where(JobAddress.job_id == job_id)
            .order_by(JobAddress.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


    async def update_address_details(
        self,
        *,
        address_id: int,
        floor: int | None,
        has_elevator: bool | None,
    ) -> JobAddress:
        stmt = select(JobAddress).where(JobAddress.id == address_id)
        result = await self.session.execute(stmt)
        address = result.scalar_one_or_none()

        if address is None:
            raise ValueError("address not found")

        address.floor = floor
        address.has_elevator = has_elevator

        await self.session.flush()

        return address

    async def add_item(self, item: JobItem) -> JobItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_items_by_job(
        self,
        job_id: int,
    ) -> list[JobItem]:
        stmt = (
            select(JobItem)
            .where(JobItem.job_id == job_id)
            .order_by(JobItem.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_offer(self, offer: JobOffer) -> JobOffer:
        self.session.add(offer)
        await self.session.flush()
        return offer

    async def list_offers_by_job(
        self,
        job_id: int,
    ) -> list[JobOffer]:
        stmt = (
            select(JobOffer)
            .where(JobOffer.job_id == job_id)
            .order_by(JobOffer.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_offer_by_id(
        self,
        offer_id: int,
    ) -> JobOffer | None:
        stmt = select(JobOffer).where(JobOffer.id == offer_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_accepted_offer_by_job_id(
        self,
        job_id: int,
    ) -> JobOffer | None:
        stmt = (
            select(JobOffer)
            .where(JobOffer.job_id == job_id)
            .where(JobOffer.status == "accepted")
            .order_by(JobOffer.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_offer_carrier_ids_by_job(self, job_id: int) -> set[int]:
        stmt = select(JobOffer.carrier_id).where(JobOffer.job_id == job_id)
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def list_expired_pending_offers(
        self,
        *,
        now,
        limit: int = 100,
    ) -> list[JobOffer]:
        stmt = (
            select(JobOffer)
            .where(JobOffer.status == "pending")
            .where(JobOffer.expires_at.is_not(None))
            .where(JobOffer.expires_at < now)
            .order_by(JobOffer.expires_at, JobOffer.id)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def expire_offer_if_pending(
        self,
        *,
        offer_id: int,
        expired_at,
    ) -> JobOffer | None:
        offer = await self.get_offer_by_id(offer_id)

        if offer is None:
            return None

        if offer.status != "pending":
            return offer

        offer.status = "expired"
        offer.responded_at = expired_at
        offer.updated_at = expired_at

        await self.session.flush()

        return offer


    async def update_assignment_confirmation_status(
        self,
        *,
        job_id: int,
        actor: str,
        status: str,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        if actor == "client":
            job.client_confirmation_status = status
        elif actor == "carrier":
            job.carrier_confirmation_status = status
        else:
            raise ValueError("invalid assignment confirmation actor")

        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def clear_assignment_confirmation_statuses(
        self,
        *,
        job_id: int,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.client_confirmation_status = None
        job.carrier_confirmation_status = None
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_offer_carrier_message(
        self,
        *,
        offer_id: int,
        chat_id: int,
        message_id: int,
        updated_at,
    ) -> JobOffer:
        offer = await self.get_offer_by_id(offer_id)

        if offer is None:
            raise ValueError("offer not found")

        offer.carrier_message_chat_id = chat_id
        offer.carrier_message_id = message_id
        offer.updated_at = updated_at

        await self.session.flush()

        return offer

    async def update_offer_status(
        self,
        offer_id: int,
        status: str,
        responded_at,
        decline_reason: str | None = None,
    ) -> JobOffer:
        offer = await self.get_offer_by_id(offer_id)

        if offer is None:
            raise ValueError("offer not found")

        offer.status = status
        offer.responded_at = responded_at
        offer.updated_at = responded_at
        if decline_reason is not None:
            offer.decline_reason = decline_reason

        await self.session.flush()

        return offer

    async def update_offer_price_and_note(
        self,
        *,
        offer_id: int,
        price_cents: int,
        carrier_note: str | None,
        updated_at,
    ) -> JobOffer:
        offer = await self.get_offer_by_id(offer_id)

        if offer is None:
            raise ValueError("offer not found")

        offer.price_cents = price_cents
        offer.carrier_note = carrier_note
        offer.updated_at = updated_at

        await self.session.flush()

        return offer

    async def cancel_accepted_offer_by_job(
        self,
        *,
        job_id: int,
        cancelled_at,
    ) -> JobOffer | None:
        accepted_offer = await self.get_accepted_offer_by_job_id(job_id)

        if accepted_offer is None:
            return None

        accepted_offer.status = "cancelled"
        accepted_offer.responded_at = cancelled_at
        accepted_offer.updated_at = cancelled_at

        await self.session.flush()

        return accepted_offer

    async def decline_pending_offers_by_job_except(
        self,
        job_id: int,
        accepted_offer_id: int,
        responded_at,
    ) -> list[JobOffer]:
        offers = await self.list_offers_by_job(job_id)
        declined: list[JobOffer] = []

        for offer in offers:
            if offer.id == accepted_offer_id:
                continue
            if offer.status != "pending":
                continue

            offer.status = "declined"
            offer.responded_at = responded_at
            offer.updated_at = responded_at
            declined.append(offer)

        await self.session.flush()
        return declined

    async def close_unselected_offers_by_job_except(
        self,
        job_id: int,
        selected_offer_id: int,
        responded_at,
    ) -> list[JobOffer]:
        offers = await self.list_offers_by_job(job_id)
        closed: list[JobOffer] = []

        for offer in offers:
            if offer.id == selected_offer_id:
                continue
            if offer.status == "pending":
                offer.status = "declined"
            elif offer.status == "accepted":
                offer.status = "cancelled"
            else:
                continue

            offer.responded_at = responded_at
            offer.updated_at = responded_at
            closed.append(offer)

        await self.session.flush()
        return closed

    async def update_job_status(
        self,
        job_id: int,
        status: str,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        previous_status = getattr(job.status, "value", job.status)
        status_value = getattr(status, "value", status)

        job.status = status_value
        job.updated_at = updated_at

        if status_value in {"assigned_pending_confirmation", "assigned"} and job.assigned_at is None:
            job.assigned_at = updated_at
        elif status_value == "in_progress" and job.started_at is None:
            job.started_at = updated_at
        elif status_value == "completed" and job.completed_at is None:
            job.completed_at = updated_at
        elif status_value == "cancelled" and job.cancelled_at is None:
            job.cancelled_at = updated_at

        if previous_status != status_value:
            self.session.add(
                JobStatusEvent(
                    job_id=job.id,
                    from_status=previous_status,
                    to_status=status_value,
                    occurred_at=updated_at,
                )
            )

        await self.session.flush()

        return job

    async def update_estimated_payload(
        self,
        job_id: int,
        estimated_payload_kg: int | None,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.estimated_payload_kg = estimated_payload_kg
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_estimated_volume(
        self,
        job_id: int,
        estimated_volume_m3: float | None,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.estimated_volume_m3 = estimated_volume_m3
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_required_loaders(
        self,
        job_id: int,
        required_loaders: int | None,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.required_loaders = required_loaders
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_needs_tail_lift(
        self,
        job_id: int,
        needs_tail_lift: bool,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.needs_tail_lift = needs_tail_lift
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_needs_crane(
        self,
        job_id: int,
        needs_crane: bool,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.needs_crane = needs_crane
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_needs_mobile_lift(
        self,
        job_id: int,
        needs_mobile_lift: bool,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.needs_mobile_lift = needs_mobile_lift
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_needs_assembly(
        self,
        job_id: int,
        needs_assembly: bool,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.needs_assembly = needs_assembly
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_needs_packing(
        self,
        job_id: int,
        needs_packing: bool,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.needs_packing = needs_packing
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_comment_and_status(
        self,
        job_id: int,
        comment: str | None,
        status: str,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        previous_status = getattr(job.status, "value", job.status)
        status_value = getattr(status, "value", status)

        job.comment = comment
        job.status = status_value
        job.updated_at = updated_at

        if previous_status != status_value:
            self.session.add(
                JobStatusEvent(
                    job_id=job.id,
                    from_status=previous_status,
                    to_status=status_value,
                    occurred_at=updated_at,
                )
            )

        await self.session.flush()

        return job

    async def add_media(self, media: JobMedia) -> JobMedia:
        self.session.add(media)
        await self.session.flush()
        return media

    async def list_media_by_job(
        self,
        job_id: int,
    ) -> list[JobMedia]:
        stmt = (
            select(JobMedia)
            .where(JobMedia.job_id == job_id)
            .order_by(JobMedia.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


    async def update_client_phone(
        self,
        job_id: int,
        client_phone: str | None,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.client_phone = client_phone
        job.updated_at = updated_at

        await self.session.flush()

        return job

    async def update_client_whatsapp(
        self,
        job_id: int,
        client_whatsapp: str | None,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.client_whatsapp = client_whatsapp
        job.updated_at = updated_at

        await self.session.flush()

        return job


    async def update_requested_date(
        self,
        job_id: int,
        requested_date,
        updated_at,
    ) -> Job:
        job = await self.get_job_by_id(job_id)

        if job is None:
            raise ValueError("job not found")

        job.requested_date = requested_date
        job.updated_at = updated_at

        await self.session.flush()

        return job
