import logging
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.email.models import EmailDeliveryStatus
from app.services.email.models import EmailEventType
from app.services.email.models import EmailMessage
from app.services.email.notification_service import recipient_domain
from app.services.email.templates import render_email
from app.services.email.transport import EmailTransport
from app.services.email.transport import PermanentEmailTransportError
from app.services.email.transport import TemporaryEmailTransportError
from app.services.tracking_url import build_tracking_url


logger = logging.getLogger(__name__)


class EmailDispatcher:
    def __init__(
        self,
        *,
        session_maker: async_sessionmaker,
        transport: EmailTransport,
        public_base_url: str,
        from_name: str,
        from_address: str,
        reply_to: str | None,
        max_attempts: int,
        retry_base_seconds: int,
    ) -> None:
        self.session_maker = session_maker
        self.transport = transport
        self.public_base_url = public_base_url
        self.from_name = from_name
        self.from_address = from_address
        self.reply_to = reply_to or None
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds

    async def dispatch_due(self, *, limit: int = 50) -> int:
        now = datetime.now(UTC)
        async with self.session_maker() as session:
            repository = JobEmailNotificationRepository(session)
            notification_ids = await repository.list_due_ids(
                now=now,
                max_attempts=self.max_attempts,
                limit=limit,
            )

        processed = 0
        for notification_id in notification_ids:
            if await self._dispatch_one(notification_id):
                processed += 1
        return processed

    async def _dispatch_one(self, notification_id: int) -> bool:
        attempted_at = datetime.now(UTC)
        async with self.session_maker() as session:
            repository = JobEmailNotificationRepository(session)
            notification = await repository.claim(
                notification_id=notification_id,
                now=attempted_at,
                max_attempts=self.max_attempts,
            )
            if notification is None:
                await session.rollback()
                return False
            await session.commit()

            snapshot = {
                "id": notification.id,
                "job_id": notification.job_id,
                "event_type": notification.event_type,
                "recipient_email": notification.recipient_email,
                "source_locale": notification.source_locale,
                "customer_name": notification.customer_name_snapshot,
                "tracking_token": notification.tracking_token_snapshot,
                "attempt_count": notification.attempt_count,
            }

        tracking_url = build_tracking_url(
            snapshot["source_locale"],
            snapshot["tracking_token"],
            self.public_base_url,
        )
        rendered = render_email(
            event_type=EmailEventType(snapshot["event_type"]),
            locale=snapshot["source_locale"],
            tracking_url=tracking_url,
            customer_name=snapshot["customer_name"],
        )
        message = EmailMessage(
            to=snapshot["recipient_email"],
            subject=rendered.subject,
            text_body=rendered.text_body,
            html_body=rendered.html_body,
            from_address=self.from_address,
            from_name=self.from_name,
            reply_to=self.reply_to,
        )

        try:
            result = await self.transport.send(message)
        except PermanentEmailTransportError:
            await self._record_failure(snapshot, permanent=True)
        except TemporaryEmailTransportError:
            await self._record_failure(snapshot, permanent=False)
        except Exception:
            logger.exception(
                "email transport raised unexpected error",
                extra={
                    "job_id": snapshot["job_id"],
                    "event_type": snapshot["event_type"],
                    "attempt_count": snapshot["attempt_count"],
                    "recipient_domain": recipient_domain(
                        snapshot["recipient_email"]
                    ),
                },
            )
            await self._record_failure(snapshot, permanent=False)
        else:
            sent_at = datetime.now(UTC)
            async with self.session_maker() as session:
                repository = JobEmailNotificationRepository(session)
                await repository.mark_sent(
                    notification_id=snapshot["id"],
                    now=sent_at,
                    provider_message_id=result.provider_message_id,
                )
                await session.commit()
            logger.info(
                "email_notification_sent",
                extra={
                    "job_id": snapshot["job_id"],
                    "event_type": snapshot["event_type"],
                    "locale": snapshot["source_locale"],
                    "attempt_count": snapshot["attempt_count"],
                    "delivery_status": EmailDeliveryStatus.SENT.value,
                    "recipient_domain": recipient_domain(
                        snapshot["recipient_email"]
                    ),
                },
            )
        return True

    async def _record_failure(
        self,
        snapshot: dict,
        *,
        permanent: bool,
    ) -> None:
        failed_at = datetime.now(UTC)
        exhausted = snapshot["attempt_count"] >= self.max_attempts
        backoff = self.retry_base_seconds * (
            2 ** (snapshot["attempt_count"] - 1)
        )
        next_attempt_at = failed_at + timedelta(seconds=backoff)
        last_error = (
            "permanent email transport failure"
            if permanent
            else "temporary email transport failure"
        )
        async with self.session_maker() as session:
            repository = JobEmailNotificationRepository(session)
            notification = await repository.mark_failed_attempt(
                notification_id=snapshot["id"],
                now=failed_at,
                next_attempt_at=next_attempt_at,
                last_error=last_error,
                permanent=permanent,
                max_attempts=self.max_attempts,
            )
            await session.commit()

        event_name = (
            "email_notification_failed"
            if permanent or exhausted
            else "email_notification_retry"
        )
        logger.warning(
            event_name,
            extra={
                "job_id": snapshot["job_id"],
                "event_type": snapshot["event_type"],
                "locale": snapshot["source_locale"],
                "attempt_count": snapshot["attempt_count"],
                "delivery_status": notification.delivery_status,
                "recipient_domain": recipient_domain(
                    snapshot["recipient_email"]
                ),
            },
        )
