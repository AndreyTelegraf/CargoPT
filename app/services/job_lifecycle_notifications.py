import logging
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.bot.completion_keyboard import build_completion_keyboard
from app.domain.requested_date import PORTUGAL_TIMEZONE
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.email.models import EmailEventType


logger = logging.getLogger(__name__)


def _format_requested_date(value: datetime | None) -> str:
    if value is None:
        return "не указана"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(PORTUGAL_TIMEZONE).strftime("%d.%m.%Y %H:%M")


async def _send_telegram_safely(bot, *, chat_id: int | None, text: str, reply_markup=None) -> None:
    if chat_id is None:
        return
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
    except Exception:
        logger.exception(
            "job lifecycle Telegram notification failed",
            extra={"chat_id": chat_id},
        )


async def _notify_job_parties(
    *,
    bot,
    job,
    accepted_offer,
    carrier_repository: CarrierRepository,
    text: str,
    reply_markup=None,
) -> None:
    await _send_telegram_safely(
        bot,
        chat_id=job.client_telegram_user_id,
        text=text,
        reply_markup=reply_markup,
    )

    if accepted_offer is None:
        return
    carrier = await carrier_repository.get_carrier_by_id(
        accepted_offer.carrier_id
    )
    if carrier is not None:
        await _send_telegram_safely(
            bot,
            chat_id=carrier.telegram_user_id,
            text=text,
            reply_markup=reply_markup,
        )


async def process_job_lifecycle_notifications(
    *,
    bot,
    session,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    timestamp = now or datetime.now(UTC)
    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)
    processed = 0

    reminder_24h_jobs = await job_repository.list_jobs_for_24h_reminder(
        now=timestamp + timedelta(hours=2),
        cutoff=timestamp + timedelta(hours=24),
        limit=limit,
    )
    for job in reminder_24h_jobs:
        accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
        text = (
            f"Напоминание по заявке #{job.id}.\n\n"
            f"Перевозка запланирована на {_format_requested_date(job.requested_date)}.\n"
            "Проверьте адреса и договорённости второй стороны."
        )
        await _notify_job_parties(
            bot=bot,
            job=job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
            text=text,
        )
        await job_repository.enqueue_email_notification(
            job=job,
            event_type=EmailEventType.MOVE_REMINDER_24H,
            now=timestamp,
        )
        await job_repository.mark_lifecycle_notification_sent(
            job_id=job.id,
            notification="reminder_24h",
            sent_at=timestamp,
        )
        processed += 1

    reminder_2h_jobs = await job_repository.list_jobs_for_2h_reminder(
        now=timestamp,
        cutoff=timestamp + timedelta(hours=2),
        limit=limit,
    )
    for job in reminder_2h_jobs:
        accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
        text = (
            f"Напоминание по заявке #{job.id}.\n\n"
            f"Перевозка запланирована на {_format_requested_date(job.requested_date)}.\n"
            "До начала осталось менее двух часов."
        )
        await _notify_job_parties(
            bot=bot,
            job=job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
            text=text,
        )
        await job_repository.enqueue_email_notification(
            job=job,
            event_type=EmailEventType.MOVE_REMINDER_2H,
            now=timestamp,
        )
        await job_repository.mark_lifecycle_notification_sent(
            job_id=job.id,
            notification="reminder_2h",
            sent_at=timestamp,
        )
        processed += 1

    completion_jobs = await job_repository.list_jobs_for_completion_prompt(
        cutoff=timestamp - timedelta(hours=2),
        not_before=timestamp - timedelta(hours=48),
        limit=limit,
    )
    for job in completion_jobs:
        accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
        text = (
            f"Запланированное время перевозки по заявке #{job.id} прошло.\n\n"
            "Подтвердите результат перевозки."
        )
        await _notify_job_parties(
            bot=bot,
            job=job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
            text=text,
            reply_markup=build_completion_keyboard(job.id),
        )
        await job_repository.enqueue_email_notification(
            job=job,
            event_type=EmailEventType.COMPLETION_REQUESTED,
            now=timestamp,
        )
        await job_repository.mark_lifecycle_notification_sent(
            job_id=job.id,
            notification="completion_prompt",
            sent_at=timestamp,
        )
        processed += 1

    return processed
