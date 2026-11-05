import json
import logging
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from aiogram.exceptions import TelegramBadRequest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.exceptions import TelegramRetryAfter
import traceback
from types import SimpleNamespace
from app.services.telegram_delivery_plan import build_delivery_plan
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import InputMediaPhoto
from aiogram.types import InputMediaVideo
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.bot.offer_keyboard import build_offer_keyboard
from app.bot.completion_keyboard import build_completion_keyboard
from app.domain.telegram_notification import TelegramDeliveryStatus
from app.domain.telegram_notification import TelegramNotificationType
from app.repositories.job import JobRepository
from app.repositories.telegram_notification import TelegramNotificationRepository


logger = logging.getLogger(__name__)


class DeliveryPersistenceError(RuntimeError):
    """A send may have succeeded; automatic replay would be unsafe."""


class TelegramNotificationDispatcher:
    def __init__(
        self,
        *,
        session_maker: async_sessionmaker,
        bot,
        max_attempts: int = 5,
        retry_base_seconds: int = 60,
        stale_sending_seconds: int = 300,
    ) -> None:
        self.session_maker = session_maker
        self.bot = bot
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds
        self.stale_sending_seconds = stale_sending_seconds

    async def dispatch_due(self, *, limit: int = 50) -> int:
        now = datetime.now(UTC)
        async with self.session_maker() as session:
            repository = TelegramNotificationRepository(session)
            recovered = await repository.recover_stale_claims(
                now=now,
                stale_before=now - timedelta(seconds=self.stale_sending_seconds),
                max_attempts=self.max_attempts,
            )
            notification_ids = await repository.list_due_ids(
                now=now,
                max_attempts=self.max_attempts,
                limit=limit,
            )
            await session.commit()

        if recovered:
            logger.warning(
                "telegram_notification_stale_claims_recovered",
                extra={"recovered_count": recovered},
            )

        processed = 0
        for notification_id in notification_ids:
            try:
                if await self._dispatch_one(notification_id):
                    processed += 1
            except Exception as exc:
                # Database failure after a successful send leaves SENDING. Recovery
                # quarantines it; never send it again merely because marking failed.
                logger.error("telegram_notification_persistence_error notification_id=%s error_type=%s stack=%s",
                             notification_id, type(exc).__name__, self._safe_stack(exc))
        return processed

    async def _dispatch_one(self, notification_id: int) -> bool:
        attempted_at = datetime.now(UTC)
        async with self.session_maker() as session:
            repository = TelegramNotificationRepository(session)
            notification = await repository.claim(
                notification_id=notification_id,
                now=attempted_at,
                max_attempts=self.max_attempts,
            )
            if notification is None:
                await session.rollback()
                return False

            media = []
            if (
                notification.notification_type
                == TelegramNotificationType.CARRIER_OFFER.value
            ):
                media = [
                    {
                        "media_type": item.media_type,
                        "telegram_file_id": item.telegram_file_id,
                    }
                    for item in await JobRepository(session).list_media_by_job(
                        notification.job_id
                    )
                ]

            snapshot = {
                "id": notification.id,
                "job_id": notification.job_id,
                "offer_id": notification.offer_id,
                "notification_type": notification.notification_type,
                "recipient_chat_id": notification.recipient_chat_id,
                "payload": json.loads(notification.payload_json or "{}"),
                "attempt_count": notification.attempt_count,
                "media": media,
            }
            await session.commit()

        try:
            message = await self._deliver(snapshot)
        except DeliveryPersistenceError:
            raise
        except (TelegramForbiddenError, TelegramBadRequest, ValueError) as exc:
            await self._record_failure(snapshot, exc=exc, permanent=True)
        except Exception as exc:
            logger.error(
                "telegram_notification_delivery_error error_type=%s stack=%s",
                type(exc).__name__, self._safe_stack(exc), extra=self._log_context(snapshot),
            )
            await self._record_failure(snapshot, exc=exc, permanent=False)
        else:
            sent_at = datetime.now(UTC)
            provider_chat_id = getattr(getattr(message, "chat", None), "id", None)
            provider_message_id = getattr(message, "message_id", None)
            async with self.session_maker() as session:
                repository = TelegramNotificationRepository(session)
                await repository.mark_sent(
                    notification_id=snapshot["id"],
                    now=sent_at,
                    provider_chat_id=provider_chat_id,
                    provider_message_id=provider_message_id,
                    expected_attempt=snapshot["attempt_count"],
                )
                if snapshot["offer_id"] is not None and message is not None:
                    await JobRepository(session).update_offer_carrier_message(
                        offer_id=snapshot["offer_id"],
                        chat_id=provider_chat_id,
                        message_id=provider_message_id,
                        updated_at=sent_at,
                    )
                lifecycle_notification = snapshot["payload"].get(
                    "lifecycle_notification"
                )
                if isinstance(lifecycle_notification, str):
                    await JobRepository(session).mark_lifecycle_notification_sent(
                        job_id=snapshot["job_id"],
                        notification=lifecycle_notification,
                        sent_at=sent_at,
                    )
                await session.commit()
            logger.info(
                "telegram_notification_sent",
                extra={
                    **self._log_context(snapshot),
                    "delivery_status": TelegramDeliveryStatus.SENT.value,
                },
            )
        return True

    async def _checkpoint(self, snapshot):
        try:
            async with self.session_maker() as session:
                await TelegramNotificationRepository(session).checkpoint(
                    notification_id=snapshot["id"], attempt_count=snapshot["attempt_count"],
                    payload_json=json.dumps(snapshot["payload"], ensure_ascii=False, sort_keys=True),
                    now=datetime.now(UTC),
                )
                await session.commit()
        except Exception as exc:
            raise DeliveryPersistenceError(type(exc).__name__) from None

    async def _deliver(self, snapshot: dict):
        progress = snapshot["payload"].get("_delivery")
        if progress is None:
            progress = {"steps": build_delivery_plan(snapshot), "completed": 0}
            snapshot["payload"]["_delivery"] = progress
            await self._checkpoint(snapshot)
        for index in range(progress["completed"], len(progress["steps"])):
            step = progress["steps"][index]
            kwargs = dict(step["kwargs"])
            markup = kwargs.get("reply_markup")
            if markup:
                kwargs["reply_markup"] = InlineKeyboardMarkup.model_validate(markup)
            if step["method"] == "send_media_group":
                kwargs["media"] = [
                    InputMediaPhoto(**item) if item["type"] == "photo" else InputMediaVideo(**item)
                    for item in kwargs["media"]
                ]
            # Check ownership and renew the lease before each external operation.
            await self._checkpoint(snapshot)
            result = await getattr(self.bot, step["method"])(
                chat_id=snapshot["recipient_chat_id"], **kwargs,
            )
            message = result[-1] if isinstance(result, list) else result
            progress.update(
                completed=index+1,
                chat_id=getattr(getattr(message, "chat", None), "id", None),
                message_id=getattr(message, "message_id", None),
            )
            # A later text failure resumes after the saved media, never at step 0.
            await self._checkpoint(snapshot)
        return SimpleNamespace(
            chat=SimpleNamespace(id=progress.get("chat_id")),
            message_id=progress.get("message_id"),
        )

    async def _record_failure(
        self,
        snapshot: dict,
        *,
        exc: Exception,
        permanent: bool,
    ) -> None:
        failed_at = datetime.now(UTC)
        backoff = self.retry_base_seconds * (2 ** (snapshot["attempt_count"] - 1))
        if isinstance(exc, TelegramRetryAfter):
            backoff = max(backoff, exc.retry_after)
        next_attempt_at = failed_at + timedelta(seconds=backoff)
        # API exception strings can contain message bodies, file ids and chat ids.
        last_error = type(exc).__name__
        async with self.session_maker() as session:
            repository = TelegramNotificationRepository(session)
            notification = await repository.mark_failed_attempt(
                notification_id=snapshot["id"],
                now=failed_at,
                next_attempt_at=next_attempt_at,
                last_error=last_error,
                permanent=permanent,
                max_attempts=self.max_attempts,
                expected_attempt=snapshot["attempt_count"],
            )
            await session.commit()

        logger.warning(
            "telegram_notification_failed"
            if notification.delivery_status == TelegramDeliveryStatus.FAILED.value
            else "telegram_notification_retry",
            extra={
                **self._log_context(snapshot),
                "delivery_status": notification.delivery_status,
                "last_error_type": type(exc).__name__,
            },
        )

    @staticmethod
    def _log_context(snapshot: dict) -> dict:
        return {
            "notification_id": snapshot["id"],
            "job_id": snapshot["job_id"],
            "offer_id": snapshot["offer_id"],
            "notification_type": snapshot["notification_type"],
            "carrier_id": snapshot["payload"].get("carrier_id"),
            "attempt_count": snapshot["attempt_count"],
        }

    @staticmethod
    def _safe_stack(exc: Exception) -> str:
        return " > ".join(f"{frame.filename}:{frame.lineno}:{frame.name}"
                          for frame in traceback.extract_tb(exc.__traceback__))
