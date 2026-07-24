import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

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
from app.services.email.dispatcher import EmailDispatcher
from app.services.email.models import EmailDeliveryStatus
from app.services.email.models import EmailEventType
from app.services.email.models import EmailSendResult
from app.services.email.notification_service import EmailNotificationService
from app.services.email.transport import TemporaryEmailTransportError


class RetryThenSuccessTransport:
    def __init__(self) -> None:
        self.calls = 0
        self.messages = []

    async def send(self, message):
        self.calls += 1
        self.messages.append(message)
        if self.calls == 1:
            raise TemporaryEmailTransportError("temporary")
        return EmailSendResult(provider_message_id="provider-123")


class AlwaysFailTransport:
    def __init__(self) -> None:
        self.calls = 0

    async def send(self, message):
        self.calls += 1
        raise TemporaryEmailTransportError("temporary")


def make_dispatcher(sessions, transport, *, max_attempts=2):
    return EmailDispatcher(
        session_maker=sessions,
        transport=transport,
        public_base_url="https://cargopt.pt",
        from_name="CargoPT",
        from_address="noreply@cargopt.pt",
        reply_to=None,
        max_attempts=max_attempts,
        retry_base_seconds=1,
    )


async def enqueue(sessions, email, event_type):
    now = datetime.now(UTC)
    async with sessions() as session:
        job = Job(
            source="web_form",
            source_locale="ru",
            customer_email=email,
            status="matching",
            tracking_token=f"token-{event_type.value}",
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        await session.flush()
        service = EmailNotificationService(
            JobEmailNotificationRepository(session),
            enabled=True,
        )
        notification = await service.enqueue_for_job(
            job=job,
            event_type=event_type,
            now=now,
        )
        await session.commit()
        return notification.id


async def make_due(sessions, notification_id):
    async with sessions() as session:
        notification = await session.get(
            JobEmailNotification,
            notification_id,
        )
        notification.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        await session.commit()


async def load(sessions, notification_id):
    async with sessions() as session:
        return await session.scalar(
            select(JobEmailNotification).where(
                JobEmailNotification.id == notification_id
            )
        )


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    notification_id = await enqueue(
        sessions,
        "retry@example.test",
        EmailEventType.REQUEST_RECEIVED,
    )
    transport = RetryThenSuccessTransport()
    dispatcher = make_dispatcher(sessions, transport)

    assert await dispatcher.dispatch_due() == 1
    after_first = await load(sessions, notification_id)
    assert after_first.delivery_status == EmailDeliveryStatus.RETRY.value
    assert after_first.attempt_count == 1
    assert after_first.next_attempt_at is not None

    await make_due(sessions, notification_id)
    assert await dispatcher.dispatch_due() == 1
    after_second = await load(sessions, notification_id)
    assert after_second.delivery_status == EmailDeliveryStatus.SENT.value
    assert after_second.attempt_count == 2
    assert after_second.provider_message_id == "provider-123"
    assert transport.calls == 2
    assert "/ru/track/" in transport.messages[0].text_body

    failed_id = await enqueue(
        sessions,
        "failed@example.test",
        EmailEventType.REQUEST_CANCELLED,
    )
    failure_transport = AlwaysFailTransport()
    failure_dispatcher = make_dispatcher(
        sessions,
        failure_transport,
        max_attempts=2,
    )
    assert await failure_dispatcher.dispatch_due() == 1
    await make_due(sessions, failed_id)
    assert await failure_dispatcher.dispatch_due() == 1
    failed = await load(sessions, failed_id)
    assert failed.delivery_status == EmailDeliveryStatus.FAILED.value
    assert failed.attempt_count == 2
    assert failed.next_attempt_at is None
    assert failure_transport.calls == 2
    assert await failure_dispatcher.dispatch_due() == 0

    await engine.dispose()
    print("EMAIL_RETRY_OK")
    print("EMAIL_PERMANENT_FAILURE_OK")


asyncio.run(main())
