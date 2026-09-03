from app.domain.job_status import JobStatus
from app.repositories.carrier import CarrierRepository
from app.services.assignment_confirmation import format_telegram_status_block


def build_carrier_assignment_confirmation_text(job) -> str:
    import html

    client_link = (
        f'<a href="tg://user?id={int(job.client_telegram_user_id)}">'
        f'{html.escape(job.client_telegram_username or "клиент", quote=False)}</a>'
        if job.client_telegram_user_id is not None
        and job.client_telegram_username
        else html.escape(job.customer_name or "S/N", quote=False)
    )
    username = (
        "@" + html.escape(job.client_telegram_username.lstrip("@"), quote=False)
        if job.client_telegram_username
        else "S/N"
    )

    return (
        f"Клиент выбрал ваше предложение по заявке №{job.id}.\n\n"
        f"Клиент: {client_link}\n"
        f"Username: {username}\n"
        f"Телефон: {html.escape(job.client_phone or 'не указан', quote=False)}\n"
        f"WhatsApp: {html.escape(job.client_whatsapp or 'не указан', quote=False)}\n\n"
        "Свяжитесь с клиентом и согласуйте детали перевозки."
    )


async def send_assignment_confirmation_requests(
    *,
    bot,
    job,
    carrier_telegram_user_id: int | None,
) -> None:
    if carrier_telegram_user_id is not None:
        await bot.send_message(
            chat_id=carrier_telegram_user_id,
            text=build_carrier_assignment_confirmation_text(job),
            parse_mode="HTML",
        )


async def send_assignment_final_notifications(
    *,
    bot,
    job,
    accepted_offer,
    carrier_repository: CarrierRepository,
) -> None:
    if job.status not in {
        JobStatus.ASSIGNED,
        JobStatus.READY_FOR_MATCHING,
        JobStatus.MANUAL_REVIEW_REQUIRED,
    }:
        return

    carrier = None
    if accepted_offer is not None:
        carrier = await carrier_repository.get_carrier_by_id(
            accepted_offer.carrier_id
        )

    if job.status == JobStatus.ASSIGNED:
        client_text = format_telegram_status_block(
            (
                f"Сделка по заявке №{job.id} подтверждена обеими сторонами.\n\n"
                "Свяжитесь с перевозчиком напрямую и согласуйте последние детали перевозки."
            ),
            state="success",
        )
        carrier_text = format_telegram_status_block(
            (
                f"Сделка по заявке №{job.id} подтверждена обеими сторонами.\n\n"
                "Свяжитесь с клиентом напрямую и согласуйте последние детали перевозки."
            ),
            state="success",
        )
    elif job.status == JobStatus.READY_FOR_MATCHING:
        client_text = format_telegram_status_block(
            (
                f"По заявке №{job.id} договориться с перевозчиком не удалось.\n\n"
                "Заявка снова в поиске. "
                "Мы отправляем её другим подходящим перевозчикам."
            ),
            state="searching",
        )
        carrier_text = format_telegram_status_block(
            (
                f"По заявке №{job.id} договориться с клиентом не удалось.\n\n"
                "Для вас эта заявка закрыта."
            ),
            state="failed",
        )
    else:
        client_text = format_telegram_status_block(
            (
                f"По заявке №{job.id} договориться с перевозчиком не удалось.\n\n"
                "До перевозки осталось меньше трёх суток, поэтому "
                "автоматическая рассылка остановлена. "
                "Заявку проверит диспетчер CargoPT."
            ),
            state="searching",
        )
        carrier_text = format_telegram_status_block(
            (
                f"По заявке №{job.id} договориться с клиентом не удалось.\n\n"
                "Для вас эта заявка закрыта."
            ),
            state="failed",
        )

    if job.client_telegram_user_id is not None:
        await bot.send_message(
            chat_id=job.client_telegram_user_id,
            text=client_text,
            parse_mode="HTML",
        )

    if carrier is not None and carrier.telegram_user_id is not None:
        await bot.send_message(
            chat_id=carrier.telegram_user_id,
            text=carrier_text,
            parse_mode="HTML",
        )
