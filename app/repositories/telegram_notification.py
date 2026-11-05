from datetime import datetime

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.telegram_notification import TelegramDeliveryStatus
from app.models.telegram_notification import TelegramNotificationOutbox


class TelegramNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_dedupe_key(
        self,
        dedupe_key: str,
    ) -> TelegramNotificationOutbox | None:
        result = await self.session.execute(
            select(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.dedupe_key == dedupe_key
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        notification_id: int,
    ) -> TelegramNotificationOutbox | None:
        result = await self.session.execute(
            select(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.id == notification_id
            )
        )
        return result.scalar_one_or_none()

    async def enqueue(
        self,
        notification: TelegramNotificationOutbox,
    ) -> TelegramNotificationOutbox:
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

    async def recover_stale_claims(
        self,
        *,
        now: datetime,
        stale_before: datetime,
        max_attempts: int,
    ) -> int:
        # A dead sender may already have reached Telegram. Do not replay an
        # ambiguous operation automatically: dispatcher review is required.
        result = await self.session.execute(
            update(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.delivery_status == TelegramDeliveryStatus.SENDING.value,
                TelegramNotificationOutbox.last_attempt_at <= stale_before,
            ).values(
                delivery_status=TelegramDeliveryStatus.UNCERTAIN.value,
                next_attempt_at=None, last_error="delivery outcome unknown after interrupted sender",
                updated_at=now,
            )
        )
        return result.rowcount

    async def list_due_ids(
        self,
        *,
        now: datetime,
        max_attempts: int,
        limit: int,
    ) -> list[int]:
        result = await self.session.execute(
            select(TelegramNotificationOutbox.id)
            .where(
                TelegramNotificationOutbox.delivery_status.in_(
                    (
                        TelegramDeliveryStatus.PENDING.value,
                        TelegramDeliveryStatus.RETRY.value,
                    )
                )
            )
            .where(TelegramNotificationOutbox.attempt_count < max_attempts)
            .where(
                or_(
                    TelegramNotificationOutbox.next_attempt_at.is_(None),
                    TelegramNotificationOutbox.next_attempt_at <= now,
                )
            )
            .order_by(
                TelegramNotificationOutbox.next_attempt_at,
                TelegramNotificationOutbox.id,
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
    ) -> TelegramNotificationOutbox | None:
        # The state transition and attempt increment are one conditional write.
        # SQLite serializes writers; cached ORM objects cannot grant a second lease.
        result = await self.session.execute(
            update(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.id == notification_id,
                TelegramNotificationOutbox.delivery_status.in_((
                    TelegramDeliveryStatus.PENDING.value, TelegramDeliveryStatus.RETRY.value,
                )),
                TelegramNotificationOutbox.attempt_count < max_attempts,
                or_(TelegramNotificationOutbox.next_attempt_at.is_(None),
                    TelegramNotificationOutbox.next_attempt_at <= now),
            ).values(
                delivery_status=TelegramDeliveryStatus.SENDING.value,
                attempt_count=TelegramNotificationOutbox.attempt_count + 1,
                last_attempt_at=now, next_attempt_at=None, updated_at=now,
            ).returning(TelegramNotificationOutbox),
            execution_options={"populate_existing": True, "synchronize_session": False},
        )
        return result.scalar_one_or_none()

    async def checkpoint(self, *, notification_id: int, attempt_count: int,
                         payload_json: str, now: datetime) -> None:
        result = await self.session.execute(
            update(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.id == notification_id,
                TelegramNotificationOutbox.delivery_status == TelegramDeliveryStatus.SENDING.value,
                TelegramNotificationOutbox.attempt_count == attempt_count,
            ).values(payload_json=payload_json, updated_at=now, last_attempt_at=now)
        )
        if result.rowcount != 1:
            raise RuntimeError("notification sending ownership lost")

    async def mark_sent(
        self,
        *,
        notification_id: int,
        now: datetime,
        provider_chat_id: int | None,
        provider_message_id: int | None,
        expected_attempt: int | None = None,
    ) -> TelegramNotificationOutbox:
        if expected_attempt is not None:
            return await self._finish_owned(notification_id, expected_attempt, dict(
                delivery_status=TelegramDeliveryStatus.SENT.value, sent_at=now,
                provider_chat_id=provider_chat_id, provider_message_id=provider_message_id,
                last_error=None, next_attempt_at=None, updated_at=now,
            ))
        notification = await self._require(notification_id)
        notification.delivery_status = TelegramDeliveryStatus.SENT.value
        notification.sent_at = now
        notification.provider_chat_id = provider_chat_id
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
        expected_attempt: int | None = None,
    ) -> TelegramNotificationOutbox:
        if expected_attempt is not None:
            terminal = permanent or expected_attempt >= max_attempts
            return await self._finish_owned(notification_id, expected_attempt, dict(
                delivery_status=TelegramDeliveryStatus.FAILED.value if terminal else TelegramDeliveryStatus.RETRY.value,
                next_attempt_at=None if terminal else next_attempt_at,
                last_error=last_error[:1000], updated_at=now,
            ))
        notification = await self._require(notification_id)
        exhausted = notification.attempt_count >= max_attempts
        if permanent or exhausted:
            notification.delivery_status = TelegramDeliveryStatus.FAILED.value
            notification.next_attempt_at = None
        else:
            notification.delivery_status = TelegramDeliveryStatus.RETRY.value
            notification.next_attempt_at = next_attempt_at
        notification.last_error = last_error[:1000]
        notification.updated_at = now
        await self.session.flush()
        return notification

    async def _finish_owned(self, notification_id, expected_attempt, values):
        result = await self.session.execute(
            update(TelegramNotificationOutbox).where(
                TelegramNotificationOutbox.id == notification_id,
                TelegramNotificationOutbox.delivery_status == TelegramDeliveryStatus.SENDING.value,
                TelegramNotificationOutbox.attempt_count == expected_attempt,
            ).values(**values).returning(TelegramNotificationOutbox),
            execution_options={"populate_existing": True, "synchronize_session": False},
        )
        notification = result.scalar_one_or_none()
        if notification is None:
            raise RuntimeError("notification sending ownership lost")
        return notification

    async def _require(
        self,
        notification_id: int,
    ) -> TelegramNotificationOutbox:
        notification = await self.get_by_id(notification_id)
        if notification is None:
            raise ValueError("Telegram notification not found")
        return notification
