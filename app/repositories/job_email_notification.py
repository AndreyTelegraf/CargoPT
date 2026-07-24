from datetime import datetime

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_email_notification import JobEmailNotification
from app.services.email.models import EmailDeliveryStatus


class JobEmailNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        notification_id: int,
    ) -> JobEmailNotification | None:
        result = await self.session.execute(
            select(JobEmailNotification).where(
                JobEmailNotification.id == notification_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_dedupe_key(
        self,
        dedupe_key: str,
    ) -> JobEmailNotification | None:
        result = await self.session.execute(
            select(JobEmailNotification).where(
                JobEmailNotification.dedupe_key == dedupe_key
            )
        )
        return result.scalar_one_or_none()

    async def enqueue(
        self,
        notification: JobEmailNotification,
    ) -> JobEmailNotification:
        existing = await self.get_by_dedupe_key(notification.dedupe_key)
        if existing is not None:
            return existing

        try:
            async with self.session.begin_nested():
                self.session.add(notification)
                await self.session.flush()
            return notification
        except IntegrityError:
            existing = await self.get_by_dedupe_key(notification.dedupe_key)
            if existing is None:
                raise
            return existing

    async def list_due_ids(
        self,
        *,
        now: datetime,
        max_attempts: int,
        limit: int,
    ) -> list[int]:
        result = await self.session.execute(
            select(JobEmailNotification.id)
            .where(
                JobEmailNotification.delivery_status.in_(
                    (
                        EmailDeliveryStatus.PENDING.value,
                        EmailDeliveryStatus.RETRY.value,
                    )
                )
            )
            .where(JobEmailNotification.attempt_count < max_attempts)
            .where(
                or_(
                    JobEmailNotification.next_attempt_at.is_(None),
                    JobEmailNotification.next_attempt_at <= now,
                )
            )
            .order_by(
                JobEmailNotification.next_attempt_at,
                JobEmailNotification.id,
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim(
        self,
        *,
        notification_id: int,
        now: datetime,
        max_attempts: int,
    ) -> JobEmailNotification | None:
        notification = await self.get_by_id(notification_id)
        if notification is None:
            return None
        if notification.delivery_status not in {
            EmailDeliveryStatus.PENDING.value,
            EmailDeliveryStatus.RETRY.value,
        }:
            return None
        if notification.attempt_count >= max_attempts:
            return None

        notification.delivery_status = EmailDeliveryStatus.SENDING.value
        notification.attempt_count += 1
        notification.last_attempt_at = now
        notification.next_attempt_at = None
        notification.updated_at = now
        await self.session.flush()
        return notification

    async def mark_sent(
        self,
        *,
        notification_id: int,
        now: datetime,
        provider_message_id: str | None,
    ) -> JobEmailNotification:
        notification = await self._require(notification_id)
        notification.delivery_status = EmailDeliveryStatus.SENT.value
        notification.sent_at = now
        notification.provider_message_id = provider_message_id
        notification.last_error = None
        notification.next_attempt_at = None
        notification.updated_at = now
        await self.session.flush()
        return notification

    async def mark_failed_attempt(
        self,
        *,
        notification_id: int,
        now: datetime,
        next_attempt_at: datetime | None,
        last_error: str,
        permanent: bool,
        max_attempts: int,
    ) -> JobEmailNotification:
        notification = await self._require(notification_id)
        exhausted = notification.attempt_count >= max_attempts
        if permanent or exhausted:
            notification.delivery_status = EmailDeliveryStatus.FAILED.value
            notification.next_attempt_at = None
        else:
            notification.delivery_status = EmailDeliveryStatus.RETRY.value
            notification.next_attempt_at = next_attempt_at
        notification.last_error = last_error
        notification.updated_at = now
        await self.session.flush()
        return notification

    async def _require(
        self,
        notification_id: int,
    ) -> JobEmailNotification:
        notification = await self.get_by_id(notification_id)
        if notification is None:
            raise ValueError("email notification not found")
        return notification
