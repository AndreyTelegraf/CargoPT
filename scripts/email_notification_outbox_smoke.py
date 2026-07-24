import asyncio
from datetime import UTC
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models
from app.models.job import Job
from app.models.job_email_notification import JobEmailNotification
from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.email.models import EmailEventType
from app.services.email.notification_service import EmailNotificationService


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now(UTC)
    async with sessions() as session:
        job = Job(
            source="web_form",
            source_locale="en",
            customer_name="Test Client",
            customer_email="client@example.test",
            preferred_contact="phone",
            status="matching",
            tracking_token="tracking-snapshot",
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        await session.flush()

        repository = JobEmailNotificationRepository(session)
        service = EmailNotificationService(repository, enabled=True)
        first = await service.enqueue_for_job(
            job=job,
            event_type=EmailEventType.REQUEST_RECEIVED,
            now=now,
        )
        second = await service.enqueue_for_job(
            job=job,
            event_type=EmailEventType.REQUEST_RECEIVED,
            now=now,
        )
        assert first is not None
        assert second is not None
        assert first.id == second.id

        disabled = EmailNotificationService(repository, enabled=False)
        skipped = await disabled.enqueue_for_job(
            job=job,
            event_type=EmailEventType.OFFER_AVAILABLE,
            now=now,
        )
        assert skipped is None

        count = await session.scalar(
            select(func.count(JobEmailNotification.id))
        )
        assert count == 1
        assert first.recipient_email == "client@example.test"
        assert first.source_locale == "en"
        assert first.tracking_token_snapshot == "tracking-snapshot"
        assert first.dedupe_key == (
            f"job:{job.id}:email:request_received"
        )

    await engine.dispose()
    print("EMAIL_OUTBOX_DEDUPE_OK")


asyncio.run(main())
