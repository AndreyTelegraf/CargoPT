from app.domain.admin_access import JOB_CONTROL_TELEGRAM_USER_IDS
from app.domain.job_status import JobStatus
from app.services.job_matching import MatchingReason
from app.services.short_lead_time_warning import should_filter_short_lead_time


def _format_matching_reason(
    reason: MatchingReason | None,
    regions: list[str] | None,
) -> str:
    if reason == MatchingReason.SHORT_LEAD_TIME:
        return (
            "До желаемого времени перевозки меньше 72 часов. "
            "Автоматическая рассылка перевозчикам не запускалась."
        )
    if reason == MatchingReason.REGION_NOT_DETERMINED:
        return "Не удалось определить регион по координатам, геокодингу или тексту адреса."
    if reason == MatchingReason.NO_ELIGIBLE_CARRIERS:
        if regions:
            return "Регион определён, но подходящих активных перевозчиков не найдено: " + ", ".join(regions)
        return "Подходящих активных перевозчиков не найдено."
    if reason == MatchingReason.NO_ADDRESSES:
        return "У заявки нет адресов для матчинга."
    if reason == MatchingReason.REGION_FROM_GEOCODING:
        return "Регион определён через геокодинг, но подходящих перевозчиков не найдено."
    if reason == MatchingReason.REGION_FROM_TEXT_FALLBACK:
        return "Регион определён только через текстовый fallback, но подходящих перевозчиков не найдено."
    return "Не удалось найти перевозчика."


def build_offer_escalation_text(
    *,
    job,
    offers,
    matching_reason: MatchingReason | None = None,
    matching_regions: list[str] | None = None,
) -> str:
    pending = sum(1 for offer in offers if offer.status == "pending")
    declined = sum(1 for offer in offers if offer.status == "declined")
    expired = sum(1 for offer in offers if offer.status == "expired")
    accepted = sum(1 for offer in offers if offer.status == "accepted")
    client_username = getattr(job, "client_telegram_username", None)
    client_telegram_user_id = getattr(job, "client_telegram_user_id", None)
    if client_username:
        client = f"@{client_username}"
    elif client_telegram_user_id:
        client = f"Telegram ID {client_telegram_user_id}"
    else:
        client = next(
            (
                value
                for value in (
                    getattr(job, "customer_name", None),
                    getattr(job, "customer_email", None),
                    getattr(job, "client_phone", None),
                    getattr(job, "client_whatsapp", None),
                )
                if value
            ),
            "контакт не указан",
        )

    if accepted:
        reason = "Есть принятое предложение, но заявка требует ручного контроля."
        accepted_line = f"Принятых предложений — {accepted}."
        recommendations = (
            "Рекомендуем:\n\n"
            "• проверить назначение перевозчика\n"
            "• проверить подтверждение клиента\n"
            "• связаться с перевозчиком"
        )
    elif matching_reason == MatchingReason.SHORT_LEAD_TIME:
        reason = _format_matching_reason(matching_reason, matching_regions)
        accepted_line = "Принятых предложений нет."
        recommendations = (
            "Рекомендуем:\n\n"
            "• связаться с клиентом и уточнить возможность переноса\n"
            "• при подтверждённой срочности решить заявку вручную\n"
            "• при необходимости отправить подходящим перевозчикам вручную"
        )
    else:
        reason = _format_matching_reason(matching_reason, matching_regions)
        accepted_line = "Принятых предложений нет."
        recommendations = (
            "Рекомендуем:\n\n"
            "• добавить новых перевозчиков\n"
            "• отправить вручную\n"
            "• связаться с клиентом"
        )

    distribution_summary = (
        "Автоматическая рассылка не запускалась."
        if matching_reason == MatchingReason.SHORT_LEAD_TIME
        else (
            "Рассылка завершена.\n\n"
            f"{len(offers)} перевозчиков получили заявку."
        )
    )

    return (
        f"Заявка #{job.id}\n\n"
        f"Клиент: {client}\n"
        f"Статус: {job.status}\n\n"
        f"Причина:\n\n"
        f"{reason}\n\n"
        f"{distribution_summary}\n\n"
        f"{declined} отказались.\n"
        f"{expired} не ответили.\n"
        f"{pending} ожидают ответа.\n\n"
        f"{accepted_line}\n\n"
        f"{recommendations}"
    )


async def notify_job_control_about_unassigned_job(
    *,
    bot,
    job,
    offers,
    matching_reason: MatchingReason | None = None,
    matching_regions: list[str] | None = None,
) -> None:
    text = build_offer_escalation_text(
        job=job,
        offers=offers,
        matching_reason=matching_reason,
        matching_regions=matching_regions,
    )

    for recipient_id in JOB_CONTROL_TELEGRAM_USER_IDS:
        await bot.send_message(chat_id=recipient_id, text=text)


async def escalate_job_to_manual_review(
    *,
    bot,
    job,
    job_repository,
    matching_reason: MatchingReason | None = None,
    matching_regions: list[str] | None = None,
) -> None:
    offers = await job_repository.list_offers_by_job(job.id)
    has_accepted_offer = any(offer.status == "accepted" for offer in offers)

    if has_accepted_offer:
        await job_repository.update_job_status(
            job_id=job.id,
            status=JobStatus.OFFERED,
            updated_at=job.updated_at,
        )
        return

    await job_repository.update_job_status(
        job_id=job.id,
        status=JobStatus.MANUAL_REVIEW_REQUIRED,
        updated_at=job.updated_at,
    )
    await notify_job_control_about_unassigned_job(
        bot=bot,
        job=job,
        offers=offers,
        matching_reason=matching_reason,
        matching_regions=matching_regions,
    )


async def hold_short_lead_job_for_manual_review(
    *,
    bot,
    job,
    job_repository,
    now=None,
) -> bool:
    if not should_filter_short_lead_time(job.requested_date, now=now):
        return False

    job.short_lead_time_filtered = True
    await escalate_job_to_manual_review(
        bot=bot,
        job=job,
        job_repository=job_repository,
        matching_reason=MatchingReason.SHORT_LEAD_TIME,
    )
    return True
