from datetime import UTC
from datetime import datetime

from app.domain.admin_access import JOB_CONTROL_TELEGRAM_USER_IDS
from app.domain.job_status import JobStatus
from app.services.job_lifecycle import InvalidJobStatusTransitionError


COMPLETION_CONFIRMED = "confirmed"
COMPLETION_PROBLEM = "problem"


async def resolve_completion_actor(
    *,
    telegram_user_id: int,
    job,
    accepted_offer,
    carrier_repository,
) -> str | None:
    if job.client_telegram_user_id == telegram_user_id:
        return "client"

    carrier = await carrier_repository.get_carrier_by_telegram_user_id(
        telegram_user_id
    )
    if carrier is None or accepted_offer is None:
        return None
    if carrier.id == accepted_offer.carrier_id:
        return "carrier"
    return None


async def record_completion_response(
    job_repository,
    *,
    job_id: int,
    actor: str,
    status: str,
    now: datetime | None = None,
):
    if actor not in {"client", "carrier"}:
        raise ValueError("invalid completion actor")
    if status not in {COMPLETION_CONFIRMED, COMPLETION_PROBLEM}:
        raise ValueError("invalid completion status")

    job = await job_repository.get_job_by_id(job_id)
    if job is None:
        raise ValueError("job not found")
    if JobStatus(job.status) not in {JobStatus.ASSIGNED, JobStatus.IN_PROGRESS}:
        raise InvalidJobStatusTransitionError(
            f"cannot record completion for job {job_id} from {job.status}"
        )
    if job.completion_prompted_at is None:
        raise InvalidJobStatusTransitionError(
            f"completion has not been requested for job {job_id}"
        )

    timestamp = now or datetime.now(UTC)
    job = await job_repository.record_completion_status(
        job_id=job_id,
        actor=actor,
        status=status,
        updated_at=timestamp,
    )

    if (
        job.client_completion_status == COMPLETION_CONFIRMED
        and job.carrier_completion_status == COMPLETION_CONFIRMED
    ):
        job = await job_repository.update_job_status(
            job_id=job_id,
            status=JobStatus.COMPLETED,
            updated_at=timestamp,
        )

    return job


async def notify_job_control_about_completion_problem(*, bot, job, actor: str) -> None:
    actor_label = "клиент" if actor == "client" else "перевозчик"
    text = (
        f"По заявке #{job.id} отмечена проблема после перевозки.\n\n"
        f"Сообщил: {actor_label}.\n"
        "Статус заявки автоматически не изменён. Требуется связаться с обеими сторонами."
    )
    for recipient_id in JOB_CONTROL_TELEGRAM_USER_IDS:
        await bot.send_message(chat_id=recipient_id, text=text)


async def send_completion_result_notifications(
    *,
    bot,
    job,
    accepted_offer,
    carrier_repository,
    completed_by_dispatcher: bool = False,
) -> None:
    carrier = None
    if accepted_offer is not None:
        carrier = await carrier_repository.get_carrier_by_id(
            accepted_offer.carrier_id
        )

    if job.status == JobStatus.COMPLETED and completed_by_dispatcher:
        client_text = f"Диспетчер CargoPT завершил заявку #{job.id}."
        carrier_text = client_text
    elif job.status == JobStatus.COMPLETED:
        client_text = (
            f"Заявка #{job.id} завершена. Обе стороны подтвердили выполнение перевозки."
        )
        carrier_text = client_text
    else:
        client_text = (
            f"Ответ по заявке #{job.id} сохранён. "
            "Ожидаем ответ второй стороны или проверку диспетчера."
        )
        carrier_text = client_text

    if job.client_telegram_user_id is not None:
        await bot.send_message(
            chat_id=job.client_telegram_user_id,
            text=client_text,
        )
    if carrier is not None and carrier.telegram_user_id is not None:
        await bot.send_message(
            chat_id=carrier.telegram_user_id,
            text=carrier_text,
        )
