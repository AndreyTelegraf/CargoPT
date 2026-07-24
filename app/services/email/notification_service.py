import logging
from datetime import UTC
from datetime import datetime

from app.models.job import Job
from app.models.job_email_notification import JobEmailNotification
from app.repositories.job_email_notification import (
    JobEmailNotificationRepository,
)
from app.services.email.models import EmailDeliveryStatus
from app.services.email.models import EmailEventType
from app.services.email.templates import normalize_email_locale


logger = logging.getLogger(__name__)


def recipient_domain(email: str) -> str:
    _, separator, domain = email.strip().lower().rpartition("@")
    return domain if separator else "invalid"


class EmailNotificationService:
    def __init__(
        self,
        repository: JobEmailNotificationRepository,
        *,
        enabled: bool,
    ) -> None:
        self.repository = repository
        self.enabled = enabled

    async def enqueue_for_job(
        self,
        *,
        job: Job,
        event_type: EmailEventType | str,
        now: datetime | None = None,
    ) -> JobEmailNotification | None:
        event = EmailEventType(event_type)
        if not self.enabled:
            logger.info(
                "email_notification_skipped",
                extra={
                    "job_id": job.id,
                    "event_type": event.value,
                    "delivery_status": EmailDeliveryStatus.SKIPPED.value,
                },
            )
            return None

        email = (job.customer_email or "").strip()
        token = (job.tracking_token or "").strip()
        if job.id is None or not email or not token:
            logger.info(
                "email_notification_skipped",
                extra={
                    "job_id": job.id,
                    "event_type": event.value,
                    "delivery_status": EmailDeliveryStatus.SKIPPED.value,
                },
            )
            return None

        timestamp = now or datetime.now(UTC)
        locale = normalize_email_locale(job.source_locale)
        notification = JobEmailNotification(
            job_id=job.id,
            event_type=event.value,
            recipient_email=email,
            source_locale=locale,
            customer_name_snapshot=job.customer_name,
            status_snapshot=str(job.status),
            tracking_token_snapshot=token,
            dedupe_key=f"job:{job.id}:email:{event.value}",
            delivery_status=EmailDeliveryStatus.PENDING.value,
            attempt_count=0,
            next_attempt_at=timestamp,
            last_attempt_at=None,
            sent_at=None,
            provider_message_id=None,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        stored = await self.repository.enqueue(notification)
        if stored is notification:
            logger.info(
                "email_notification_enqueued",
                extra={
                    "job_id": job.id,
                    "event_type": event.value,
                    "locale": locale,
                    "attempt_count": 0,
                    "delivery_status": EmailDeliveryStatus.PENDING.value,
                    "recipient_domain": recipient_domain(email),
                },
            )
        return stored
