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
from app.models.job import JobAddress
from app.models.job import JobItem
from app.models.job_email_notification import JobEmailNotification
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.email.models import EmailEventType
from app.services.email.notification_service import EmailNotificationService
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService


class ForbiddenBot:
    def __getattr__(self, name):
        raise AssertionError(f"duplicate path used bot: {name}")


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with sessions() as session:
        job = Job(
            source="web_form",
            source_locale="ru",
            customer_name="Клиент",
            customer_email="client@example.test",
            preferred_contact="email",
            client_phone=None,
            client_whatsapp=None,
            status="offered",
            tracking_token="existing-tracking-token",
            requested_date=None,
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=False,
            needs_crane=False,
            needs_mobile_lift=False,
            required_loaders=1,
            estimated_payload_kg=None,
            estimated_volume_m3=None,
            comment=None,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        await session.flush()
        session.add_all(
            (
                JobAddress(
                    job_id=job.id,
                    kind="pickup",
                    raw_text="Lisboa",
                    created_at=now,
                ),
                JobAddress(
                    job_id=job.id,
                    kind="dropoff",
                    raw_text="Porto",
                    created_at=now,
                ),
                JobItem(
                    job_id=job.id,
                    description="Caixas",
                    quantity=3,
                    created_at=now,
                ),
            )
        )
        await session.flush()

        email_service = EmailNotificationService(
            JobEmailNotificationRepository(session),
            enabled=True,
        )
        first = await email_service.enqueue_for_job(
            job=job,
            event_type=EmailEventType.REQUEST_RECEIVED,
            now=now,
        )
        assert first is not None

        service = RequestIntakeService(
            job_repository=JobRepository(session),
            carrier_repository=CarrierRepository(session),
            bot=ForbiddenBot(),
            email_notification_service=email_service,
        )
        result = await service.submit_web_intake(
            RequestIntakeInput(
                source_locale="ru",
                customer_name="Клиент",
                customer_email="client@example.test",
                preferred_contact="email",
                client_phone=None,
                client_whatsapp=None,
                utm_source=None,
                utm_medium=None,
                utm_campaign=None,
                utm_content=None,
                landing_version=None,
                requested_date=None,
                addresses=(
                    RequestIntakeAddress("pickup", "Lisboa"),
                    RequestIntakeAddress("dropoff", "Porto"),
                ),
                items=(RequestIntakeItem("Caixas", 3),),
                required_loaders=1,
            )
        )
        assert result.job.id == job.id

        count = await session.scalar(
            select(func.count(JobEmailNotification.id))
        )
        assert count == 1
        await session.commit()

    await engine.dispose()
    print("EMAIL_DUPLICATE_REQUEST_NO_RESEND_OK")


asyncio.run(main())
