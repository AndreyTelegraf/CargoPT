from dataclasses import dataclass
from datetime import UTC
from datetime import datetime

from app.domain.job_status import JobStatus
from app.domain.requested_date import validate_requested_date_not_in_past
from app.models.job import Job
from app.repositories.job import JobRepository


@dataclass(frozen=True)
class TelegramDraftInput:
    client_telegram_user_id: int
    client_telegram_username: str | None


@dataclass(frozen=True)
class WebDraftInput:
    source_locale: str | None
    customer_name: str | None
    customer_email: str | None
    preferred_contact: str | None
    client_phone: str | None
    client_whatsapp: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    utm_content: str | None
    landing_version: str | None
    requested_date: datetime | None
    referrer_host: str | None = None
    fbclid: str | None = None
    needs_assembly: bool = False
    needs_packing: bool = False
    needs_tail_lift: bool = False
    needs_crane: bool = False
    needs_mobile_lift: bool = False
    required_loaders: int | None = None
    estimated_payload_kg: int | None = None
    estimated_volume_m3: float | None = None


class RequestCreationService:
    def __init__(self, *, job_repository: JobRepository) -> None:
        self.job_repository = job_repository

    async def create_telegram_draft(self, payload: TelegramDraftInput) -> Job:
        now = datetime.now(UTC)
        job = Job(
            client_telegram_user_id=payload.client_telegram_user_id,
            client_telegram_username=payload.client_telegram_username,
            source=None,
            source_locale=None,
            customer_name=None,
            customer_email=None,
            preferred_contact=None,
            client_phone=None,
            client_whatsapp=None,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            utm_content=None,
            referrer_host=None,
            fbclid=None,
            landing_version=None,
            status=JobStatus.DRAFT,
            draft_step="pickup_address",
            requested_date=None,
            assigned_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            client_confirmation_status=None,
            carrier_confirmation_status=None,
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=False,
            needs_crane=False,
            needs_mobile_lift=False,
            required_loaders=None,
            estimated_payload_kg=None,
            estimated_volume_m3=None,
            comment=None,
            created_at=now,
            updated_at=now,
        )
        return await self.job_repository.create_job(job)

    async def create_web_draft(self, payload: WebDraftInput) -> Job:
        validate_requested_date_not_in_past(payload.requested_date)
        now = datetime.now(UTC)
        job = Job(
            client_telegram_user_id=None,
            client_telegram_username=None,
            source="web_form",
            source_locale=payload.source_locale,
            customer_name=payload.customer_name,
            customer_email=payload.customer_email,
            preferred_contact=payload.preferred_contact,
            client_phone=payload.client_phone,
            client_whatsapp=payload.client_whatsapp,
            utm_source=payload.utm_source,
            utm_medium=payload.utm_medium,
            utm_campaign=payload.utm_campaign,
            utm_content=payload.utm_content,
            referrer_host=payload.referrer_host,
            fbclid=payload.fbclid,
            landing_version=payload.landing_version,
            status=JobStatus.DRAFT,
            draft_step=None,
            requested_date=payload.requested_date,
            assigned_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            client_confirmation_status=None,
            carrier_confirmation_status=None,
            needs_assembly=payload.needs_assembly,
            needs_packing=payload.needs_packing,
            needs_tail_lift=payload.needs_tail_lift,
            needs_crane=payload.needs_crane,
            needs_mobile_lift=payload.needs_mobile_lift,
            required_loaders=payload.required_loaders,
            estimated_payload_kg=payload.estimated_payload_kg,
            estimated_volume_m3=payload.estimated_volume_m3,
            comment=None,
            created_at=now,
            updated_at=now,
        )
        return await self.job_repository.create_job(job)
