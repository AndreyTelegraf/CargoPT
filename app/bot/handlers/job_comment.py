from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import support_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.repositories.telegram_notification import TelegramNotificationRepository
from app.services.request_submission import ClientJobLimitError
from app.services.request_submission import RequestSubmissionService
from app.services.short_lead_time_warning import has_short_lead_time
from app.services.short_lead_time_warning import normalize_warning_locale
from app.services.short_lead_time_warning import short_lead_time_warning_text
from app.services.telegram_notifications import TelegramNotificationEnqueueService

router = Router()


_SUBMISSION_STATUS_COPY = {
    "pt": {
        "queued": (
            "Pedido recebido.\n\nFoi colocado na fila para {count} transportadores "
            "adequados. Receberá uma notificação quando chegar uma proposta."
        ),
        "sent": (
            "Pedido publicado.\n\nFoi enviado a {count} transportadores adequados. "
            "Receberá uma notificação quando chegar uma proposta."
        ),
        "no_carriers": (
            "Pedido publicado.\n\nNeste momento, não encontrámos transportadores "
            "adequados no sistema. A equipa CargoPT irá verificar o pedido manualmente."
        ),
    },
    "en": {
        "queued": (
            "Request received.\n\nIt has been queued for {count} suitable carriers. "
            "You will be notified when an offer arrives."
        ),
        "sent": (
            "Request published.\n\nIt has been sent to {count} suitable carriers. "
            "You will be notified when an offer arrives."
        ),
        "no_carriers": (
            "Request published.\n\nWe could not find suitable carriers in the system "
            "at the moment. The CargoPT team will review the request manually."
        ),
    },
    "ru": {
        "queued": (
            "Заявка принята.\n\nОна поставлена в очередь для подходящих перевозчиков: "
            "{count}. Вы получите уведомление, когда поступит предложение."
        ),
        "sent": (
            "Заявка опубликована.\n\nМы отправили её подходящим перевозчикам: {count}. "
            "Вы получите уведомление, когда поступит предложение."
        ),
        "no_carriers": (
            "Заявка опубликована.\n\nСейчас в системе нет подходящих перевозчиков. "
            "Команда CargoPT проверит заявку вручную."
        ),
    },
}


def _submission_status_text(
    locale: str | None,
    *,
    queued_count: int,
    sent_count: int,
) -> str:
    normalized_locale = normalize_warning_locale(
        locale,
        default_locale="ru",
    )
    copy = _SUBMISSION_STATUS_COPY[normalized_locale]
    if queued_count > 0:
        return copy["queued"].format(count=queued_count)
    if sent_count > 0:
        return copy["sent"].format(count=sent_count)
    return copy["no_carriers"]


@router.message(JobRequestStates.comment)
async def job_comment(
    message: Message,
    state: FSMContext,
) -> None:
    raw_comment = (message.text or "").strip()
    comment = None if raw_comment in {"", "-", "Без комментария"} else raw_comment

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        submission = RequestSubmissionService(
            job_repository=job_repository,
            carrier_repository=carrier_repository,
            bot=message.bot,
            telegram_notification_service=TelegramNotificationEnqueueService(
                TelegramNotificationRepository(session),
                job_repository=job_repository,
                carrier_repository=carrier_repository,
            ),
        )

        try:
            result = await submission.submit_existing_job(
                job_id=job_id,
                comment=comment,
                client_telegram_user_id=message.from_user.id,
                enforce_telegram_client_limits=True,
            )
        except ClientJobLimitError as exc:
            if str(exc) == "active_job_limit_reached":
                await message.answer(
                    "У вас уже есть 2 активные заявки. "
                    "Дождитесь ответа по одной из них или отмените лишнюю через диспетчера: https://t.me/andreytelegraf"
                )
            elif str(exc) == "daily_sent_job_limit_reached":
                await message.answer(
                    "Лимит CargoPT: не больше 3 отправленных заявок за 24 часа. "
                    "Попробуйте позже или напишите диспетчеру: https://t.me/andreytelegraf"
                )
            else:
                raise

            await session.rollback()
            return

        sent_count = result.sent_count
        queued_count = result.queued_count
        await session.commit()

    await state.clear()

    response_parts = []
    if has_short_lead_time(result.job.requested_date):
        response_parts.append(
            short_lead_time_warning_text(
                message.from_user.language_code,
                default_locale="ru",
            )
        )
    response_parts.append(
        _submission_status_text(
            message.from_user.language_code,
            queued_count=queued_count,
            sent_count=sent_count,
        )
    )
    await message.answer(
        "\n\n".join(response_parts),
        reply_markup=support_keyboard(),
    )
