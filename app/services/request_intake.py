from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.email.models import EmailEventType
from app.services.email.notification_service import EmailNotificationService
from app.services.request_creation import RequestCreationService
from app.services.request_creation import WebDraftInput
from app.services.request_population import RequestPopulationAddress
from app.services.request_population import RequestPopulationItem
from app.services.request_population import RequestPopulationService
from app.services.request_submission import RequestSubmissionResult
from app.services.request_submission import RequestSubmissionService


@dataclass(frozen=True)
class RequestIntakeAddress:
    kind: str
    raw_text: str
    floor: int | None = None
    has_elevator: bool | None = None


@dataclass(frozen=True)
class RequestIntakeItem:
    description: str
    quantity: int | None = None


@dataclass(frozen=True)
class RequestIntakeInput:
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
    addresses: tuple[RequestIntakeAddress, ...]
    items: tuple[RequestIntakeItem, ...]
    needs_assembly: bool = False
    needs_packing: bool = False
    needs_tail_lift: bool = False
    needs_crane: bool = False
    needs_mobile_lift: bool = False
    required_loaders: int | None = None
    estimated_payload_kg: int | None = None
    estimated_volume_m3: float | None = None
    comment: str | None = None


class RequestIntakeService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        carrier_repository: CarrierRepository,
        bot,
        email_notification_service: EmailNotificationService | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository
        self.bot = bot
        self.email_notification_service = email_notification_service

    @staticmethod
    def _normalized_text(value: str | None) -> str:
        return " ".join((value or "").strip().casefold().split())

    @classmethod
    def _is_identical_request(cls, job, request: RequestIntakeInput) -> bool:
        job_addresses = sorted(
            (
                address.kind,
                cls._normalized_text(address.raw_text),
                address.floor,
                address.has_elevator,
            )
            for address in (job.addresses or [])
        )
        request_addresses = sorted(
            (
                address.kind,
                cls._normalized_text(address.raw_text),
                address.floor,
                address.has_elevator,
            )
            for address in request.addresses
        )

        job_items = sorted(
            (
                cls._normalized_text(item.description),
                item.quantity,
            )
            for item in (job.items or [])
        )
        request_items = sorted(
            (
                cls._normalized_text(item.description),
                item.quantity,
            )
            for item in request.items
        )

        return (
            job.source_locale == request.source_locale
            and job.requested_date == request.requested_date
            and bool(job.needs_assembly) == request.needs_assembly
            and bool(job.needs_packing) == request.needs_packing
            and bool(job.needs_tail_lift) == request.needs_tail_lift
            and bool(job.needs_crane) == request.needs_crane
            and bool(job.needs_mobile_lift) == request.needs_mobile_lift
            and job.required_loaders == request.required_loaders
            and job.estimated_payload_kg == request.estimated_payload_kg
            and job.estimated_volume_m3 == request.estimated_volume_m3
            and cls._normalized_text(job.comment)
            == cls._normalized_text(request.comment)
            and job_addresses == request_addresses
            and job_items == request_items
        )

    async def submit_web_intake(
        self,
        request: RequestIntakeInput,
    ) -> RequestSubmissionResult:
        duplicate_cutoff = datetime.now(UTC) - timedelta(minutes=15)
        recent_jobs = await self.job_repository.list_recent_web_jobs_for_contact(
            since=duplicate_cutoff,
            customer_email=request.customer_email,
            client_phone=request.client_phone,
            client_whatsapp=request.client_whatsapp,
        )

        duplicate_job = next(
            (
                job
                for job in recent_jobs
                if self._is_identical_request(job, request)
            ),
            None,
        )

        if duplicate_job is not None:
            existing_offers = await self.job_repository.list_offers_by_job(
                duplicate_job.id
            )
            return RequestSubmissionResult(
                job=duplicate_job,
                offers_count=len(existing_offers),
                sent_count=sum(
                    offer.carrier_message_id is not None
                    for offer in existing_offers
                ),
            )

        creation = RequestCreationService(job_repository=self.job_repository)
        job = await creation.create_web_draft(
            WebDraftInput(
                source_locale=request.source_locale,
                customer_name=request.customer_name,
                customer_email=request.customer_email,
                preferred_contact=request.preferred_contact,
                client_phone=request.client_phone,
                client_whatsapp=request.client_whatsapp,
                utm_source=request.utm_source,
                utm_medium=request.utm_medium,
                utm_campaign=request.utm_campaign,
                utm_content=request.utm_content,
                landing_version=request.landing_version,
                requested_date=request.requested_date,
                needs_assembly=request.needs_assembly,
                needs_packing=request.needs_packing,
                needs_tail_lift=request.needs_tail_lift,
                needs_crane=request.needs_crane,
                needs_mobile_lift=request.needs_mobile_lift,
                required_loaders=request.required_loaders,
                estimated_payload_kg=request.estimated_payload_kg,
                estimated_volume_m3=request.estimated_volume_m3,
            )
        )

        population = RequestPopulationService(job_repository=self.job_repository)
        await population.populate(
            job_id=job.id,
            addresses=tuple(
                RequestPopulationAddress(
                    kind=address.kind,
                    raw_text=address.raw_text,
                    floor=address.floor,
                    has_elevator=address.has_elevator,
                )
                for address in request.addresses
            ),
            items=tuple(
                RequestPopulationItem(
                    description=item.description,
                    quantity=item.quantity,
                )
                for item in request.items
            ),
        )

        submission_service = RequestSubmissionService(
            job_repository=self.job_repository,
            carrier_repository=self.carrier_repository,
            bot=self.bot,
        )
        result = await submission_service.submit_existing_job(
            job_id=job.id,
            comment=request.comment,
            enforce_telegram_client_limits=False,
        )
        if self.email_notification_service is not None:
            await self.email_notification_service.enqueue_for_job(
                job=result.job,
                event_type=EmailEventType.REQUEST_RECEIVED,
            )
        return result
