from dataclasses import dataclass
from datetime import datetime

from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
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
    ) -> None:
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository
        self.bot = bot

    async def submit_web_intake(
        self,
        request: RequestIntakeInput,
    ) -> RequestSubmissionResult:
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
        return await submission_service.submit_existing_job(
            job_id=job.id,
            comment=request.comment,
            enforce_telegram_client_limits=False,
        )
