from datetime import UTC
from datetime import datetime

from app.domain.job_status import JobStatus
from app.models.job import Job
from app.repositories.carrier import CarrierRepository
from app.services.job_lifecycle import InvalidJobStatusTransitionError


ASSIGNMENT_CONFIRMATION_CONFIRMED = "confirmed"
ASSIGNMENT_CONFIRMATION_FAILED = "failed"


def build_assignment_status_from_action(action: str) -> str:
    if action == "confirm":
        return ASSIGNMENT_CONFIRMATION_CONFIRMED
    if action == "fail":
        return ASSIGNMENT_CONFIRMATION_FAILED
    raise InvalidAssignmentConfirmationStatusError("invalid assignment action")


def parse_assignment_callback(data: str) -> tuple[str, int]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "assignment":
        raise ValueError("invalid callback data")

    action = parts[1]
    job_id = int(parts[2])

    if action not in {"confirm", "fail"}:
        raise ValueError("invalid assignment action")

    return action, job_id


def build_assignment_cleanup_target(*, job: Job, accepted_offer) -> tuple[bool, int | None, int | None]:
    should_delete = job.status == JobStatus.READY_FOR_MATCHING

    if accepted_offer is None:
        return should_delete, None, None

    return (
        should_delete,
        accepted_offer.carrier_message_chat_id,
        accepted_offer.carrier_message_id,
    )


def build_assignment_offer_distribution(*, job_repository, carrier_repository):
    from app.services.carrier_search import CarrierSearchService
    from app.services.job_matching import JobMatchingService
    from app.services.job_offer import JobOfferService
    from app.services.offer_distribution import OfferDistributionService

    return OfferDistributionService(
        matching_service=JobMatchingService(
            CarrierSearchService(carrier_repository)
        ),
        offer_service=JobOfferService(job_repository),
        job_repository=job_repository,
    )


async def process_assignment_failure_redispatch(
    *,
    bot,
    job,
    accepted_offer,
    job_repository,
    carrier_repository,
):
    (
        should_delete_carrier_offer,
        carrier_message_chat_id,
        carrier_message_id,
    ) = build_assignment_cleanup_target(
        job=job,
        accepted_offer=accepted_offer,
    )

    if should_delete_carrier_offer:
        distribution = build_assignment_offer_distribution(
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

        new_offers = await distribution.create_offers_for_job(
            job,
            limit=5,
            expires_in_minutes=60,
        )

        from app.services.offer_notification import send_job_offers_to_carriers

        await send_job_offers_to_carriers(
            bot=bot,
            job=job,
            offers=new_offers,
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

    return (
        should_delete_carrier_offer,
        carrier_message_chat_id,
        carrier_message_id,
    )


class InvalidAssignmentConfirmationActorError(ValueError):
    pass


class InvalidAssignmentConfirmationStatusError(ValueError):
    pass


async def resolve_assignment_actor(
    *,
    telegram_user_id: int,
    job,
    accepted_offer,
    carrier_repository: CarrierRepository,
) -> str | None:
    if job.client_telegram_user_id == telegram_user_id:
        return "client"

    carrier = await carrier_repository.get_carrier_by_telegram_user_id(telegram_user_id)
    if carrier is None or accepted_offer is None:
        return None

    if accepted_offer.carrier_id == carrier.id:
        return "carrier"

    return None


async def evaluate_assignment_confirmation(job_repository, *, job_id: int) -> Job:
    job = await job_repository.get_job_by_id(job_id)

    if job is None:
        raise ValueError("job not found")

    current_status = JobStatus(job.status)
    if current_status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
        raise InvalidJobStatusTransitionError(
            f"cannot evaluate assignment confirmation for job {job_id} from {current_status}"
        )

    votes = {
        job.client_confirmation_status,
        job.carrier_confirmation_status,
    }

    if ASSIGNMENT_CONFIRMATION_FAILED in votes:
        now = datetime.now(UTC)
        await job_repository.cancel_accepted_offer_by_job(
            job_id=job_id,
            cancelled_at=now,
        )
        await job_repository.clear_assignment_confirmation_statuses(
            job_id=job_id,
            updated_at=now,
        )
        return await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.READY_FOR_MATCHING,
            updated_at=datetime.now(UTC),
        )

    if (
        job.client_confirmation_status == ASSIGNMENT_CONFIRMATION_CONFIRMED
        and job.carrier_confirmation_status == ASSIGNMENT_CONFIRMATION_CONFIRMED
    ):
        return await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.ASSIGNED,
            updated_at=datetime.now(UTC),
        )

    return job


async def record_assignment_confirmation(
    job_repository,
    *,
    job_id: int,
    actor: str,
    status: str,
) -> Job:
    if actor not in {"client", "carrier"}:
        raise InvalidAssignmentConfirmationActorError("invalid assignment confirmation actor")

    if status not in {
        ASSIGNMENT_CONFIRMATION_CONFIRMED,
        ASSIGNMENT_CONFIRMATION_FAILED,
    }:
        raise InvalidAssignmentConfirmationStatusError("invalid assignment confirmation status")

    job = await job_repository.get_job_by_id(job_id)

    if job is None:
        raise ValueError("job not found")

    if JobStatus(job.status) != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
        raise InvalidJobStatusTransitionError(
            f"cannot record assignment confirmation for job {job_id} from {job.status}"
        )

    await job_repository.update_assignment_confirmation_status(
        job_id=job_id,
        actor=actor,
        status=status,
        updated_at=datetime.now(UTC),
    )

    return await evaluate_assignment_confirmation(job_repository, job_id=job_id)


def build_assignment_result_text(*, job_id: int, action: str, job_status: str) -> str:
    if job_status == JobStatus.ASSIGNED:
        return f"Сделка по заявке №{job_id} подтверждена обеими сторонами."

    if job_status == JobStatus.READY_FOR_MATCHING:
        return (
            f"По заявке №{job_id} сделка не состоялась. "
            "Заявка возвращена в активный поиск."
        )

    if action == "confirm":
        return (
            f"Ваше подтверждение по заявке №{job_id} принято. "
            "Ждём ответ второй стороны."
        )

    return (
        f"Ваш ответ по заявке №{job_id} принят. "
        "Заявка будет возвращена в активный поиск."
    )
