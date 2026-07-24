import asyncio
from datetime import UTC
from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models
from app.models.job_email_notification import JobEmailNotification
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.email.models import EmailEventType
from app.services.email.notification_service import EmailNotificationService
from app.services.request_creation import RequestCreationService
from app.services.request_creation import TelegramDraftInput
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService


class FakeBot:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, *, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


def request(
    email: str | None,
    *,
    pickup: str,
    locale: str = "en",
) -> RequestIntakeInput:
    return RequestIntakeInput(
        source_locale=locale,
        customer_name="Web Client",
        customer_email=email,
        preferred_contact="phone",
        client_phone=None,
        client_whatsapp=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        landing_version=None,
        requested_date=None,
        addresses=(
            RequestIntakeAddress(kind="pickup", raw_text=pickup),
            RequestIntakeAddress(kind="dropoff", raw_text="Porto"),
        ),
        items=(RequestIntakeItem(description="Boxes", quantity=3),),
    )


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        job_repository = JobRepository(session)
        email_repository = JobEmailNotificationRepository(session)
        service = RequestIntakeService(
            job_repository=job_repository,
            carrier_repository=CarrierRepository(session),
            bot=FakeBot(),
            email_notification_service=EmailNotificationService(
                email_repository,
                enabled=True,
            ),
        )

        for locale, pickup in (
            ("pt", "Lisboa"),
            ("en", "Coimbra"),
            ("ru", "Braga"),
        ):
            with_email = await service.submit_web_intake(
                request(
                    f"client-{locale}@example.test",
                    pickup=pickup,
                    locale=locale,
                )
            )
            assert with_email.job.customer_email == (
                f"client-{locale}@example.test"
            )

            queued = await session.scalar(
                select(JobEmailNotification).where(
                    JobEmailNotification.job_id == with_email.job.id
                )
            )
            assert queued is not None
            assert queued.event_type == EmailEventType.REQUEST_RECEIVED.value
            assert queued.source_locale == locale

        without_email = await service.submit_web_intake(
            request(None, pickup="Faro")
        )
        without_count = await session.scalar(
            select(func.count(JobEmailNotification.id)).where(
                JobEmailNotification.job_id == without_email.job.id
            )
        )
        assert without_count == 0

        telegram_job = await RequestCreationService(
            job_repository=job_repository
        ).create_telegram_draft(
            TelegramDraftInput(
                client_telegram_user_id=12345,
                client_telegram_username="client",
            )
        )
        telegram_count = await session.scalar(
            select(func.count(JobEmailNotification.id)).where(
                JobEmailNotification.job_id == telegram_job.id
            )
        )
        assert telegram_count == 0

        await session.commit()

    await engine.dispose()
    print("EMAIL_REQUEST_RECEIVED_PT_OK")
    print("EMAIL_REQUEST_RECEIVED_EN_OK")
    print("EMAIL_REQUEST_RECEIVED_RU_OK")
    print("EMAIL_REQUEST_WITHOUT_EMAIL_SKIPPED_OK")
    print("EMAIL_TELEGRAM_REQUEST_SKIPPED_OK")


asyncio.run(main())
