from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import support_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.request_submission import ClientJobLimitError
from app.services.request_submission import RequestSubmissionService
from app.services.short_lead_time_warning import has_short_lead_time
from app.services.short_lead_time_warning import short_lead_time_warning_text

router = Router()


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
        await session.commit()

    await state.clear()

    if sent_count > 0:
        await message.answer(
            "Заявка опубликована.\n\n"
            f"Мы отправили её подходящим перевозчикам: {sent_count}. "
            "Как только кто-то примет заказ, вы получите уведомление.",
            reply_markup=support_keyboard(),
        )
    else:
        await message.answer(
            "Заявка опубликована.\n\n"
            "Сейчас в системе нет подходящих перевозчиков. "
            "Диспетчер CargoPT проверит заявку вручную.",
            reply_markup=support_keyboard(),
        )

    if has_short_lead_time(result.job.requested_date):
        await message.answer(
            short_lead_time_warning_text(
                message.from_user.language_code,
                default_locale="ru",
            ),
            reply_markup=support_keyboard(),
        )
