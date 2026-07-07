from aiogram import F
from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from app.bot.assignment_confirmation_keyboard import build_assignment_failure_reason_keyboard
from app.db.session import async_session_maker
from app.domain.job_decline_reason import is_valid_decline_reason
from app.domain.job_status import JobStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import build_assignment_cleanup_target
from app.services.assignment_confirmation import build_assignment_result_text
from app.services.assignment_confirmation import build_assignment_status_from_action
from app.services.assignment_confirmation import parse_assignment_callback
from app.services.assignment_confirmation import process_assignment_failure_redispatch
from app.services.assignment_confirmation import record_assignment_confirmation
from app.services.assignment_confirmation import resolve_assignment_actor
from app.services.job_lifecycle import InvalidJobStatusTransitionError

router = Router()


async def _delete_message_by_id_safely(bot, *, chat_id: int | None, message_id: int | None) -> None:
    if chat_id is None or message_id is None:
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        return


async def _send_assignment_final_notifications(
    *,
    bot,
    job,
    accepted_offer,
    carrier_repository: CarrierRepository,
) -> None:
    if job.status not in {JobStatus.ASSIGNED, JobStatus.READY_FOR_MATCHING}:
        return

    carrier = None
    if accepted_offer is not None:
        carrier = await carrier_repository.get_carrier_by_id(accepted_offer.carrier_id)

    if job.status == JobStatus.ASSIGNED:
        client_text = (
            f"Сделка по заявке №{job.id} подтверждена обеими сторонами.\n\n"
            "Свяжитесь с перевозчиком напрямую и согласуйте последние детали перевозки."
        )
        carrier_text = (
            f"Сделка по заявке №{job.id} подтверждена обеими сторонами.\n\n"
            "Свяжитесь с клиентом напрямую и согласуйте последние детали перевозки."
        )
    else:
        client_text = (
            f"По заявке №{job.id} сделка не состоялась.\n\n"
            "Заявка возвращена в поиск. Мы уже ищем нового перевозчика."
        )
        carrier_text = (
            "Спасибо.\n\n"
            "Заявка возвращена в поиск."
        )

    await bot.send_message(chat_id=job.client_telegram_user_id, text=client_text)

    if carrier is not None and carrier.telegram_user_id is not None:
        await bot.send_message(chat_id=carrier.telegram_user_id, text=carrier_text)


@router.callback_query(F.data.startswith("assignment:"))
async def handle_assignment_confirmation(callback: CallbackQuery) -> None:
    raw_data = callback.data or ""
    failure_reason = None

    if raw_data.startswith("assignment:fail_reason:"):
        parts = raw_data.split(":")
        if len(parts) != 4:
            await callback.answer("Некорректная кнопка", show_alert=True)
            return

        try:
            job_id = int(parts[2])
        except ValueError:
            await callback.answer("Некорректная кнопка", show_alert=True)
            return

        failure_reason = parts[3]
        if not is_valid_decline_reason(failure_reason):
            await callback.answer("Некорректная причина", show_alert=True)
            return

        action = "fail"
    else:
        try:
            action, job_id = parse_assignment_callback(raw_data)
        except ValueError:
            await callback.answer("Некорректная кнопка", show_alert=True)
            return

    if action == "fail" and failure_reason is None:
        if callback.message:
            await callback.message.edit_text(
                "Укажите причину, почему сделка не состоялась.",
                reply_markup=build_assignment_failure_reason_keyboard(job_id),
            )
        await callback.answer()
        return

    telegram_user_id = callback.from_user.id

    async with async_session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        job = await job_repository.get_job_by_id(job_id)
        accepted_offer = await job_repository.get_accepted_offer_by_job_id(job_id)

        if job is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        if failure_reason is not None and accepted_offer is None:
            await callback.answer("Оффер не найден.", show_alert=True)
            return

        actor = await resolve_assignment_actor(
            telegram_user_id=telegram_user_id,
            job=job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
        )

        if actor is None:
            await callback.answer("Эта кнопка не для вас.", show_alert=True)
            return

        if job.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
            await callback.answer("Статус заявки уже изменён.", show_alert=True)
            return

        confirmation_status = build_assignment_status_from_action(action)

        if failure_reason is not None:
            accepted_offer.decline_reason = failure_reason

        try:
            updated_job = await record_assignment_confirmation(
                job_repository,
                job_id=job_id,
                actor=actor,
                status=confirmation_status,
            )
            result_text = build_assignment_result_text(
                job_id=job_id,
                action=action,
                job_status=updated_job.status,
            )
        except InvalidJobStatusTransitionError:
            await session.rollback()
            await callback.answer("Статус заявки уже изменён.", show_alert=True)
            return

        (
            should_delete_carrier_offer,
            carrier_message_chat_id,
            carrier_message_id,
        ) = await process_assignment_failure_redispatch(
            bot=callback.bot,
            job=updated_job,
            accepted_offer=accepted_offer,
            job_repository=job_repository,
            carrier_repository=carrier_repository,
        )

        await _send_assignment_final_notifications(
            bot=callback.bot,
            job=updated_job,
            accepted_offer=accepted_offer,
            carrier_repository=carrier_repository,
        )

        await session.commit()

    if should_delete_carrier_offer:
        await _delete_message_by_id_safely(
            callback.bot,
            chat_id=carrier_message_chat_id,
            message_id=carrier_message_id,
        )

    if callback.message:
        try:
            await callback.message.edit_text(result_text, reply_markup=None)
        except TelegramBadRequest:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except TelegramBadRequest:
                pass

    await callback.answer(result_text, show_alert=True)
