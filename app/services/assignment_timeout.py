from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.domain.job_status import JobStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import format_telegram_status_block
from app.services.assignment_confirmation import process_assignment_failure_redispatch


async def process_stale_assignment_confirmations(
    *,
    bot,
    session,
    timeout_hours: int = 24,
    limit: int = 50,
) -> int:
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=timeout_hours)

    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    jobs = await job_repository.list_stale_assigned_pending_confirmation_jobs(
        cutoff=cutoff,
        limit=limit,
    )

    processed = 0

    for job in jobs:
        accepted_offer = await job_repository.cancel_accepted_offer_by_job(
            job_id=job.id,
            cancelled_at=now,
        )
        await job_repository.clear_assignment_confirmation_statuses(
            job_id=job.id,
            updated_at=now,
        )
        updated_job = await job_repository.update_job_status(
            job_id=job.id,
            status=JobStatus.READY_FOR_MATCHING,
            updated_at=now,
        )

        await process_assignment_failure_redispatch(
            bot=bot,
            job=updated_job,
            accepted_offer=accepted_offer,
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

        if job.client_telegram_user_id is not None:
            if updated_job.status == JobStatus.MANUAL_REVIEW_REQUIRED:
                client_text = (
                    f"По заявке №{job.id} подтверждение не было получено вовремя.\n\n"
                    "До перевозки осталось меньше трёх суток, поэтому "
                    "автоматическая рассылка остановлена. "
                    "Заявку проверит диспетчер CargoPT."
                )
            else:
                client_text = (
                    f"По заявке №{job.id} подтверждение не было получено вовремя.\n\n"
                    "Заявка снова в поиске. "
                    "Мы отправляем её другим подходящим перевозчикам."
                )
            await bot.send_message(
                chat_id=job.client_telegram_user_id,
                text=format_telegram_status_block(
                    client_text,
                    state="searching",
                ),
            )

        if accepted_offer is not None:
            carrier = await carrier_repository.get_carrier_by_id(accepted_offer.carrier_id)
            if carrier is not None and carrier.telegram_user_id is not None:
                await bot.send_message(
                    chat_id=carrier.telegram_user_id,
                    text=format_telegram_status_block(
                        (
                            f"По заявке №{job.id} подтверждение не было получено вовремя.\n\n"
                            "Для вас эта заявка закрыта."
                        ),
                        state="failed",
                    ),
                )

        processed += 1

    return processed
