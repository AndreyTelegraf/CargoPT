from app.bot.handlers.carrier_invite_admin import ADMIN_TELEGRAM_USER_IDS
from app.domain.job_status import JobStatus


def build_offer_escalation_text(*, job, offers) -> str:
    pending = sum(1 for offer in offers if offer.status == "pending")
    declined = sum(1 for offer in offers if offer.status == "declined")
    expired = sum(1 for offer in offers if offer.status == "expired")
    accepted = sum(1 for offer in offers if offer.status == "accepted")
    client = job.client_telegram_username or str(job.client_telegram_user_id)

    if accepted:
        reason = "Есть принятое предложение, но заявка требует ручного контроля."
        accepted_line = f"Принятых предложений — {accepted}."
        recommendations = (
            "Рекомендуем:\n\n"
            "• проверить назначение перевозчика\n"
            "• проверить подтверждение клиента\n"
            "• связаться с перевозчиком"
        )
    else:
        reason = "Не удалось найти перевозчика."
        accepted_line = "Принятых предложений нет."
        recommendations = (
            "Рекомендуем:\n\n"
            "• добавить новых перевозчиков\n"
            "• отправить вручную\n"
            "• связаться с клиентом"
        )

    return (
        f"Заявка #{job.id}\n\n"
        f"Клиент: @{client}\n"
        f"Статус: {job.status}\n\n"
        f"Причина:\n\n"
        f"{reason}\n\n"
        f"Рассылка завершена.\n\n"
        f"{len(offers)} перевозчиков получили заявку.\n\n"
        f"{declined} отказались.\n"
        f"{expired} не ответили.\n"
        f"{pending} ожидают ответа.\n\n"
        f"{accepted_line}\n\n"
        f"{recommendations}"
    )


async def notify_admins_about_unassigned_job(*, bot, job, offers) -> None:
    text = build_offer_escalation_text(job=job, offers=offers)

    for admin_id in ADMIN_TELEGRAM_USER_IDS:
        await bot.send_message(chat_id=admin_id, text=text)


async def escalate_job_to_manual_review(
    *,
    bot,
    job,
    job_repository,
) -> None:
    offers = await job_repository.list_offers_by_job(job.id)
    await job_repository.update_job_status(
        job_id=job.id,
        status=JobStatus.MANUAL_REVIEW_REQUIRED,
        updated_at=job.updated_at,
    )
    await notify_admins_about_unassigned_job(
        bot=bot,
        job=job,
        offers=offers,
    )
