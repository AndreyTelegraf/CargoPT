import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models
from app.domain.job_offer_status import JobOfferStatus
from app.domain.job_status import JobStatus
from app.models.job import Job
from app.models.job import JobOffer
from app.models.job_email_notification import JobEmailNotification
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import (
    ASSIGNMENT_CONFIRMATION_CONFIRMED,
)
from app.services.assignment_confirmation import record_assignment_confirmation
from app.services.email.models import EmailEventType
from app.services.job_lifecycle import cancel_job
from app.services.job_offer import JobOfferService


async def event_counts(session, job_id):
    rows = (
        await session.execute(
            select(
                JobEmailNotification.event_type,
                func.count(JobEmailNotification.id),
            )
            .where(JobEmailNotification.job_id == job_id)
            .group_by(JobEmailNotification.event_type)
        )
    ).all()
    return dict(rows)


def make_offer(*, job_id: int, offer_id: int, now: datetime) -> JobOffer:
    return JobOffer(
        id=offer_id,
        job_id=job_id,
        carrier_id=offer_id,
        vehicle_id=offer_id,
        status=JobOfferStatus.PENDING,
        offered_at=now,
        expires_at=now + timedelta(hours=1),
        created_at=now,
        updated_at=now,
    )


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with sessions() as session:
        repository = JobRepository(session, email_enabled=True)
        job = await repository.create_job(
            Job(
                source="web_form",
                source_locale="pt",
                customer_name="Cliente",
                customer_email="client@example.test",
                preferred_contact="phone",
                status=JobStatus.MATCHING,
                tracking_token="status-event-token",
                requested_date=None,
                assigned_at=None,
                started_at=None,
                completed_at=None,
                cancelled_at=None,
                client_confirmation_status=None,
                carrier_confirmation_status=None,
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                created_at=now,
                updated_at=now,
            )
        )
        first = make_offer(job_id=job.id, offer_id=1001, now=now)
        second = make_offer(job_id=job.id, offer_id=1002, now=now)
        session.add_all((first, second))
        await session.flush()

        # Internal carrier offers are not yet visible to the client.
        await repository.update_job_status(
            job.id,
            JobStatus.OFFERED,
            now,
        )
        assert await event_counts(session, job.id) == {}

        service = JobOfferService(repository)
        await service.accept_offer_without_assignment(first.id)
        assert await event_counts(session, job.id) == {
            EmailEventType.OFFER_AVAILABLE.value: 1,
        }

        await service.accept_offer_without_assignment(second.id)
        assert await event_counts(session, job.id) == {
            EmailEventType.OFFER_AVAILABLE.value: 1,
        }

        await service.select_accepted_offer_for_client(
            job_id=job.id,
            offer_id=first.id,
        )
        assert await event_counts(session, job.id) == {
            EmailEventType.OFFER_AVAILABLE.value: 1,
            EmailEventType.CARRIER_SELECTED.value: 1,
        }

        await record_assignment_confirmation(
            repository,
            job_id=job.id,
            actor="client",
            status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
        )
        await record_assignment_confirmation(
            repository,
            job_id=job.id,
            actor="carrier",
            status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
        )
        assert await event_counts(session, job.id) == {
            EmailEventType.OFFER_AVAILABLE.value: 1,
            EmailEventType.CARRIER_SELECTED.value: 1,
            EmailEventType.ASSIGNMENT_CONFIRMED.value: 1,
        }

        await cancel_job(repository, job_id=job.id)
        await repository.update_job_status(
            job.id,
            JobStatus.CANCELLED,
            datetime.now(UTC),
        )
        assert await event_counts(session, job.id) == {
            EmailEventType.OFFER_AVAILABLE.value: 1,
            EmailEventType.CARRIER_SELECTED.value: 1,
            EmailEventType.ASSIGNMENT_CONFIRMED.value: 1,
            EmailEventType.REQUEST_CANCELLED.value: 1,
        }

        await session.commit()

    await engine.dispose()
    print("EMAIL_FIRST_OFFER_ONLY_OK")
    print("EMAIL_CARRIER_SELECTED_OK")
    print("EMAIL_ASSIGNMENT_CONFIRMED_OK")
    print("EMAIL_REQUEST_CANCELLED_OK")


asyncio.run(main())
