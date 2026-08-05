from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.job_completion import COMPLETION_CONFIRMED
from app.services.job_completion import COMPLETION_PROBLEM
from app.services.job_completion import notify_job_control_about_completion_problem
from app.services.job_completion import record_completion_response
from app.services.job_completion import resolve_completion_actor
from app.services.job_completion import send_completion_result_notifications
from app.services.job_lifecycle import InvalidJobStatusTransitionError


router = Router()


@router.callback_query(F.data.startswith("completion:"))
async def handle_job_completion(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or parts[1] not in {"confirm", "problem"}:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return
    try:
        job_id = int(parts[2])
    except ValueError:
        await callback.answer("Некорректная кнопка.", show_alert=True)
        return

    completion_status = (
        COMPLETION_CONFIRMED if parts[1] == "confirm" else COMPLETION_PROBLEM
    )

    async with async_session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        job = await job_repository.get_job_by_id(job_id)
        accepted_offer = await job_repository.get_accepted_offer_by_job_id(job_id)
        if job is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        actor = await resolve_completion_actor(
            telegram_user_id=callback.from_user.id,
            job=job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
        )
        if actor is None:
            await callback.answer("Эта кнопка не для вас.", show_alert=True)
            return

        try:
            updated_job = await record_completion_response(
                job_repository,
                job_id=job_id,
                actor=actor,
                status=completion_status,
            )
        except InvalidJobStatusTransitionError:
            await session.rollback()
            await callback.answer("Статус заявки уже изменён.", show_alert=True)
            return

        if completion_status == COMPLETION_PROBLEM:
            await notify_job_control_about_completion_problem(
                bot=callback.bot,
                job=updated_job,
                actor=actor,
            )

        await send_completion_result_notifications(
            bot=callback.bot,
            job=updated_job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
        )
        await session.commit()

    if callback.message:
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass
    result_text = (
        "Перевозка завершена. Ожидаем подтверждение второй стороны."
        if completion_status == COMPLETION_CONFIRMED
        else "Проблема зафиксирована. Диспетчер свяжется с обеими сторонами."
    )
    if str(updated_job.status) == "completed":
        result_text = "Заявка завершена: обе стороны подтвердили перевозку."
    await callback.answer(result_text, show_alert=True)
