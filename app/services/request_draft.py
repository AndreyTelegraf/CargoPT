from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.domain.job_status import JobStatus
from app.models.job import Job
from app.repositories.job import JobRepository
from app.services.request_creation import RequestCreationService
from app.services.request_creation import TelegramDraftInput


class ClientBannedError(ValueError):
    pass


@dataclass(frozen=True)
class RequestDraftResult:
    job: Job
    reused_existing_draft: bool
    resume_step: str


def draft_has_no_progress(job, addresses, items) -> bool:
    return (
        not addresses
        and not items
        and job.requested_date is None
        and job.estimated_payload_kg is None
        and job.estimated_volume_m3 is None
        and job.required_loaders is None
        and job.client_phone is None
        and job.client_whatsapp is None
        and job.comment is None
    )


def infer_draft_step(job, addresses, items) -> str:
    if job.draft_step:
        return job.draft_step

    pickup = next((address for address in addresses if address.kind == "pickup"), None)
    dropoff = next(
        (
            address
            for address in addresses
            if address.kind in {"dropoff", "delivery"}
        ),
        None,
    )
    if pickup is None:
        return "pickup_address"
    if pickup.floor is None or pickup.has_elevator is None:
        return "pickup_details"
    if dropoff is None:
        return "dropoff_address"
    if dropoff.floor is None or dropoff.has_elevator is None:
        return "dropoff_details"
    if job.requested_date is None:
        return "requested_datetime"
    if not items:
        return "item_description"
    if job.estimated_volume_m3 is None:
        return "media"
    if job.required_loaders is None:
        return "required_loaders"
    if job.client_phone is None and job.client_whatsapp is None:
        return "contact_phone"
    if job.client_whatsapp is None:
        return "contact_whatsapp"
    return "comment"


class RequestDraftService:
    def __init__(self, *, job_repository: JobRepository) -> None:
        self.job_repository = job_repository

    async def create_or_reuse_telegram_draft(
        self,
        *,
        client_telegram_user_id: int,
        client_telegram_username: str | None,
    ) -> RequestDraftResult:
        ban = await self.job_repository.get_active_client_ban(client_telegram_user_id)
        if ban is not None:
            raise ClientBannedError("client_banned")

        latest_draft = await self.job_repository.get_latest_draft_job_by_client_id(
            client_telegram_user_id
        )

        if latest_draft is not None:
            addresses = await self.job_repository.list_addresses_by_job(latest_draft.id)
            items = await self.job_repository.list_items_by_job(latest_draft.id)
        else:
            addresses = []
            items = []

        recent_cutoff = datetime.now(UTC) - timedelta(days=30)
        latest_updated_at = (
            latest_draft.updated_at if latest_draft is not None else None
        )
        if latest_updated_at is not None and latest_updated_at.tzinfo is None:
            latest_updated_at = latest_updated_at.replace(tzinfo=UTC)

        if latest_draft is not None and latest_updated_at >= recent_cutoff:
            resume_step = infer_draft_step(latest_draft, addresses, items)
            return RequestDraftResult(
                job=latest_draft,
                reused_existing_draft=True,
                resume_step=resume_step,
            )

        creation = RequestCreationService(job_repository=self.job_repository)
        job = await creation.create_telegram_draft(
            TelegramDraftInput(
                client_telegram_user_id=client_telegram_user_id,
                client_telegram_username=client_telegram_username,
            )
        )

        return RequestDraftResult(
            job=job,
            reused_existing_draft=False,
            resume_step="pickup_address",
        )
