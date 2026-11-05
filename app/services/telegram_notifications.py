import json
import logging
from datetime import UTC
from datetime import datetime

from app.domain.telegram_notification import TelegramDeliveryStatus
from app.domain.telegram_notification import TelegramNotificationType
from app.models.telegram_notification import TelegramNotificationOutbox
from app.repositories.telegram_notification import TelegramNotificationRepository
from app.services.job_escalation import build_offer_escalation_text
from app.services.offer_notification import build_offer_text


logger = logging.getLogger(__name__)


class TelegramNotificationEnqueueService:
    def __init__(
        self,
        repository: TelegramNotificationRepository,
        *,
        job_repository,
        carrier_repository,
    ) -> None:
        self.repository = repository
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository

    async def enqueue_message(
        self, *, job, recipient_chat_id, event_key: str, text: str,
        reply_markup=None, parse_mode=None, offer_id=None,
    ):
        """Persist a business message in the caller's transaction, never send."""
        if recipient_chat_id is None:
            return None
        now = datetime.now(UTC)
        return await self.repository.enqueue(TelegramNotificationOutbox(
            job_id=job.id, offer_id=None,
            notification_type=TelegramNotificationType.LIFECYCLE_MESSAGE.value,
            recipient_chat_id=recipient_chat_id,
            dedupe_key=f"job:{job.id}:{event_key}:{recipient_chat_id}",
            payload_json=json.dumps({
                "text": text, "parse_mode": parse_mode,
                "event_offer_id": offer_id,
                "reply_markup": reply_markup.model_dump(mode="json") if reply_markup else None,
            }, ensure_ascii=False, sort_keys=True),
            delivery_status=TelegramDeliveryStatus.PENDING.value,
            attempt_count=0, next_attempt_at=now, created_at=now, updated_at=now,
        ))

    async def enqueue_carrier_offers(
        self,
        *,
        job,
        offers,
        now: datetime | None = None,
    ) -> list[TelegramNotificationOutbox]:
        timestamp = now or datetime.now(UTC)
        items = await self.job_repository.list_items_by_job(job.id)
        addresses = await self.job_repository.list_addresses_by_job(job.id)
        pickup = next(
            (address for address in addresses if address.kind == "pickup"),
            None,
        )
        dropoff = next(
            (address for address in addresses if address.kind == "dropoff"),
            None,
        )
        stored_notifications = []

        for offer in offers:
            carrier = await self.carrier_repository.get_carrier_by_vehicle_id(
                offer.vehicle_id
            )
            if carrier is None or carrier.telegram_user_id is None:
                continue
            offer_text = build_offer_text(
                job,
                items,
                pickup,
                dropoff,
                locale=carrier.preferred_locale,
            )

            notification = TelegramNotificationOutbox(
                job_id=job.id,
                offer_id=offer.id,
                notification_type=TelegramNotificationType.CARRIER_OFFER.value,
                recipient_chat_id=carrier.telegram_user_id,
                dedupe_key=f"job:{job.id}:offer:{offer.id}:carrier_initial",
                payload_json=json.dumps(
                    {
                        "text": offer_text,
                        "parse_mode": "HTML",
                        "locale": carrier.preferred_locale,
                        "carrier_id": offer.carrier_id,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                delivery_status=TelegramDeliveryStatus.PENDING.value,
                attempt_count=0,
                next_attempt_at=timestamp,
                last_attempt_at=None,
                sent_at=None,
                provider_chat_id=None,
                provider_message_id=None,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            stored = await self.repository.enqueue(notification)
            stored_notifications.append(stored)
            if stored is not None:
                logger.info(
                    "telegram_notification_registered notification_id=%s job_id=%s offer_id=%s",
                    stored.id, stored.job_id, stored.offer_id,
                    extra={
                        "job_id": job.id,
                        "offer_id": offer.id,
                        "notification_type": notification.notification_type,
                        "delivery_status": notification.delivery_status,
                    },
                )

        return stored_notifications

    async def enqueue_manual_review(
        self,
        *,
        job,
        offers,
        recipient_chat_ids,
        matching_reason=None,
        matching_regions=None,
        now: datetime | None = None,
    ) -> list[TelegramNotificationOutbox]:
        timestamp = now or datetime.now(UTC)
        text = build_offer_escalation_text(
            job=job,
            offers=offers,
            matching_reason=matching_reason,
            matching_regions=matching_regions,
        )
        stored_notifications = []

        for recipient_chat_id in recipient_chat_ids:
            notification = TelegramNotificationOutbox(
                job_id=job.id,
                offer_id=None,
                notification_type=TelegramNotificationType.MANUAL_REVIEW.value,
                recipient_chat_id=recipient_chat_id,
                dedupe_key=f"job:{job.id}:manual_review:{recipient_chat_id}",
                payload_json=json.dumps(
                    {"text": text},
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                delivery_status=TelegramDeliveryStatus.PENDING.value,
                attempt_count=0,
                next_attempt_at=timestamp,
                last_attempt_at=None,
                sent_at=None,
                provider_chat_id=None,
                provider_message_id=None,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            stored = await self.repository.enqueue(notification)
            stored_notifications.append(stored)
            if stored is not None:
                logger.info(
                    "telegram_notification_registered notification_id=%s job_id=%s offer_id=%s",
                    stored.id, stored.job_id, stored.offer_id,
                    extra={
                        "job_id": job.id,
                        "notification_type": notification.notification_type,
                        "delivery_status": notification.delivery_status,
                    },
                )

        return stored_notifications

    async def enqueue_lifecycle_messages(
        self,
        *,
        job,
        recipient_chat_ids,
        text: str,
        lifecycle_notification: str,
        completion_keyboard: bool = False,
        now: datetime | None = None,
    ) -> list[TelegramNotificationOutbox]:
        timestamp = now or datetime.now(UTC)
        stored_notifications = []

        for recipient_chat_id in dict.fromkeys(recipient_chat_ids):
            if recipient_chat_id is None:
                continue
            notification = TelegramNotificationOutbox(
                job_id=job.id,
                offer_id=None,
                notification_type=(
                    TelegramNotificationType.LIFECYCLE_MESSAGE.value
                ),
                recipient_chat_id=recipient_chat_id,
                dedupe_key=(
                    f"job:{job.id}:lifecycle:{lifecycle_notification}:"
                    f"{recipient_chat_id}"
                ),
                payload_json=json.dumps(
                    {
                        "text": text,
                        "lifecycle_notification": lifecycle_notification,
                        "completion_keyboard": completion_keyboard,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                delivery_status=TelegramDeliveryStatus.PENDING.value,
                attempt_count=0,
                next_attempt_at=timestamp,
                last_attempt_at=None,
                sent_at=None,
                provider_chat_id=None,
                provider_message_id=None,
                last_error=None,
                created_at=timestamp,
                updated_at=timestamp,
            )
            stored = await self.repository.enqueue(notification)
            stored_notifications.append(stored)
            if stored is not None:
                logger.info(
                    "telegram_notification_registered notification_id=%s job_id=%s offer_id=%s",
                    stored.id, stored.job_id, stored.offer_id,
                    extra={
                        "job_id": job.id,
                        "notification_type": notification.notification_type,
                        "lifecycle_notification": lifecycle_notification,
                        "delivery_status": notification.delivery_status,
                    },
                )

        return stored_notifications


def notification_service_for(job_repository, carrier_repository=None):
    """Share the business session; enqueue and status changes commit together."""
    from app.repositories.carrier import CarrierRepository
    return TelegramNotificationEnqueueService(
        TelegramNotificationRepository(job_repository.session),
        job_repository=job_repository,
        carrier_repository=carrier_repository or CarrierRepository(job_repository.session),
    )
