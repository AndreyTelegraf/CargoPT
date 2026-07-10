import html
import re
from datetime import UTC
from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.types import Message

from app.domain.job_status import JobStatus
from app.domain.job_decline_reason import is_valid_decline_reason
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.job_offer import ClientOfferSelectionError
from app.services.job_offer import JobAlreadyAssignedError
from app.services.job_offer import JobOfferService
from app.services.job_offer import OfferAlreadyResolvedError
from app.services.job_offer import parse_offer_callback
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService
from app.services.offer_distribution import OfferDistributionService
from app.services.job_escalation import escalate_job_to_manual_review
from app.services.offer_notification import send_job_offers_to_carriers
from app.services.assignment_confirmation import format_telegram_status_block
from app.services.client_offer_presentation import ClientOfferPresentationService
from app.bot.offer_keyboard import build_client_offer_selection_keyboard
from app.bot.offer_keyboard import build_offer_decline_reason_keyboard
from app.bot.offer_keyboard import parse_client_offer_selection_callback
from app.bot.assignment_confirmation_keyboard import build_client_reopen_assignment_keyboard
from app.bot.states.offer_response import OfferResponseStates

router = Router()

_offer_price_input_re = re.compile(
    r"^\s*(?P<price>\d+(?:[.,]\d{1,2})?)\s*(?P<note>.*)$",
    re.DOTALL,
)


def _parse_offer_price_input(text: str) -> tuple[int, str | None]:
    match = _offer_price_input_re.match(text)

    if match is None:
        raise ValueError("invalid offer price")

    price_text = match.group("price").replace(",", ".")
    price = float(price_text)

    if price <= 0:
        raise ValueError("invalid offer price")

    price_cents = int(round(price * 100))
    note = match.group("note").strip() or None

    return price_cents, note


async def _prompt_offer_price(
    callback: CallbackQuery,
    state: FSMContext,
    offer_id: int,
) -> None:
    if callback.message is None:
        await callback.answer("Не удалось открыть ввод цены.", show_alert=True)
        return

    await state.clear()
    await state.update_data(offer_price_offer_id=offer_id)
    await state.set_state(OfferResponseStates.price)

    await callback.message.answer(
        (
            "Ответьте ценой предложения в евро.\n\n"
            "Например:\n"
            "120\n"
            "или:\n"
            "120 Подъём и разгрузка включены"
        )
    )
    await callback.answer("Введите цену ответным сообщением.")


async def _delete_message_safely(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        await message.edit_reply_markup(reply_markup=None)


async def _delete_message_by_id_safely(bot, *, chat_id: int | None, message_id: int | None) -> None:
    if chat_id is None or message_id is None:
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest:
        return


async def _finalize_offer_message(message: Message, text: str, reply_markup=None) -> None:
    if message.text is not None:
        await message.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
        return

    if message.caption is not None:
        await message.edit_caption(caption=text, parse_mode="HTML", reply_markup=reply_markup)
        return

    await message.edit_reply_markup(reply_markup=reply_markup)

def _build_accepted_offer_final_text(message: Message, status_text: str) -> str:
    original_text = message.text or message.caption or ""
    original_text = original_text.strip()

    stale_prompt = "Примите или отклоните заявку."
    if original_text.endswith(stale_prompt):
        original_text = original_text[: -len(stale_prompt)].rstrip()

    status_block = format_telegram_status_block(status_text, state="searching")

    if original_text:
        return f"{original_text}\n\n{status_block}"

    return status_block


def _format_client_offer_value(value, suffix: str = "") -> str:
    if value is None:
        return "не указано"
    return html.escape(f"{value}{suffix}", quote=False)


def build_client_offer_selection_text(job_id: int, offers) -> str:
    lines = [
        f"<b>Перевозчики откликнулись на заявку №{job_id}</b>",
        "",
        "Выберите подходящее предложение:",
    ]

    for index, offer in enumerate(offers, start=1):
        lines.extend(
            [
                "",
                f"<b>Предложение {index}</b>",
                f"Компания: {html.escape(offer.company_name, quote=False)}",
                f"Машина: {html.escape(offer.vehicle_type, quote=False)}",
                f"Грузоподъёмность: {_format_client_offer_value(offer.payload_kg, ' кг')}",
                f"Объём: {_format_client_offer_value(offer.volume_m3, ' м³')}",
                f"Грузчики: {_format_client_offer_value(offer.max_loaders)}",
            ]
        )

        if offer.price_cents is not None:
            lines.append(f"Цена: {offer.price_cents / 100:.2f} €")

        if offer.carrier_note:
            lines.append(f"Комментарий: {html.escape(offer.carrier_note, quote=False)}")

    return "\n".join(lines)


async def send_client_offer_selection_message(
    *,
    bot,
    job,
    job_repository: JobRepository,
    carrier_repository: CarrierRepository,
) -> bool:
    if job is None or job.client_telegram_user_id is None:
        return False

    presentation = ClientOfferPresentationService(
        job_repository=job_repository,
        carrier_repository=carrier_repository,
    )
    views = await presentation.list_accepted_offer_views(job.id)

    if not views:
        return False

    await bot.send_message(
        chat_id=job.client_telegram_user_id,
        text=build_client_offer_selection_text(job.id, views),
        reply_markup=build_client_offer_selection_keyboard(views),
        parse_mode="HTML",
    )

    return True


def build_client_assignment_confirmation_text(job_id: int, carrier=None) -> str:
    if carrier is None:
        return (
            f"Предложение по заявке №{job_id} выбрано.\n\n"
            "Свяжитесь с перевозчиком и согласуйте детали перевозки."
        )

    carrier_label = carrier.contact_name or carrier.company_name or "перевозчик"
    carrier_link = (
        f'<a href="tg://user?id={int(carrier.telegram_user_id)}">{html.escape(carrier_label, quote=False)}</a>'
        if carrier.telegram_user_id is not None
        else "не указан"
    )
    username = (
        "@" + html.escape(carrier.telegram_username.lstrip("@"), quote=False)
        if carrier.telegram_username
        else "не указан"
    )

    return (
        f"Предложение по заявке №{job_id} выбрано.\n\n"
        f"Перевозчик: {carrier_link}\n"
        f"Компания: {html.escape(carrier.company_name or 'не указана', quote=False)}\n"
        f"Контакт: {html.escape(carrier.contact_name or 'не указан', quote=False)}\n"
        f"Username: {username}\n"
        f"Телефон: {html.escape(carrier.phone or 'не указан', quote=False)}\n\n"
        "Свяжитесь с перевозчиком и согласуйте детали перевозки.\n\nЕсли договориться не получится, нажмите «Не договорились с перевозчиком» — мы вернём заявку в подбор."
    )


def build_carrier_assignment_confirmation_text(job) -> str:
    client_link = (
        f'<a href="tg://user?id={int(job.client_telegram_user_id)}">{html.escape(job.client_telegram_username or "клиент", quote=False)}</a>'
        if job.client_telegram_user_id is not None and job.client_telegram_username
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


@router.callback_query(F.data.startswith("offer:"))
async def handle_offer_response(callback: CallbackQuery, state: FSMContext) -> None:
    try:
        action, offer_id = parse_offer_callback(callback.data or "")
    except ValueError:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    telegram_user_id = callback.from_user.id
    sibling_offer_message_refs: list[tuple[int | None, int | None]] = []
    job = None

    async with async_session_maker() as session:
        carrier_repository = CarrierRepository(session)
        job_repository = JobRepository(session)
        offer_service = JobOfferService(job_repository)

        carrier = await carrier_repository.get_carrier_by_telegram_user_id(
            telegram_user_id
        )

        offer = await job_repository.get_offer_by_id(offer_id)

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await callback.answer("Оффер не найден", show_alert=True)
            return

        if action == "accept":
            if offer.status != "pending":
                await callback.answer("Этот оффер уже обработан.", show_alert=True)
                return

            await _prompt_offer_price(callback, state, offer_id)
            return
        else:
            if callback.message:
                await callback.message.edit_reply_markup(
                    reply_markup=build_offer_decline_reason_keyboard(offer_id),
                )
            await callback.answer("Укажите причину отказа.")
            return

        await session.commit()

    if callback.message:
        if action == "accept":
            await _finalize_offer_message(
                callback.message,
                _build_accepted_offer_final_text(callback.message, message_text),
            )
        else:
            await _delete_message_safely(callback.message)

    for chat_id, message_id in sibling_offer_message_refs:
        await _delete_message_by_id_safely(
            callback.bot,
            chat_id=chat_id,
            message_id=message_id,
        )

    await callback.answer()

@router.message(OfferResponseStates.price)
async def handle_offer_price_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    offer_id = data.get("offer_price_offer_id")

    if offer_id is None:
        await state.clear()
        await message.answer("Не удалось определить заявку. Нажмите «Принять» ещё раз.")
        return

    payload = (message.text or "").strip()
    try:
        price_cents, carrier_note = _parse_offer_price_input(payload)
    except ValueError:
        await message.answer(
            "Не удалось распознать цену. Введите число в евро, например: 120"
        )
        return

    telegram_user_id = message.from_user.id if message.from_user else None
    if telegram_user_id is None:
        await state.clear()
        await message.answer("Не удалось определить перевозчика.")
        return

    job = None
    accepted_offer = None
    message_text = (
        "Спасибо. Ваш отклик отправлен. "
        "Клиент получит предложения от перевозчиков и выберет подходящее."
    )

    async with async_session_maker() as session:
        carrier_repository = CarrierRepository(session)
        job_repository = JobRepository(session)
        offer_service = JobOfferService(job_repository)

        carrier = await carrier_repository.get_carrier_by_telegram_user_id(
            telegram_user_id
        )
        offer = await job_repository.get_offer_by_id(int(offer_id))

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await session.rollback()
            await state.clear()
            await message.answer("Оффер не найден.")
            return

        if offer.status != "pending":
            await session.rollback()
            await state.clear()
            await message.answer("Этот оффер уже обработан.")
            return

        try:
            await job_repository.update_offer_price_and_note(
                offer_id=offer.id,
                price_cents=price_cents,
                carrier_note=carrier_note,
                updated_at=datetime.now(UTC),
            )
            accepted_offer = await offer_service.accept_offer_without_assignment(offer.id)
        except OfferAlreadyResolvedError:
            await session.rollback()
            await state.clear()
            await message.answer("Этот оффер уже обработан.")
            return
        except JobAlreadyAssignedError:
            await session.rollback()
            await state.clear()
            await message.answer("Заявка уже не принимает предложения.")
            return

        job = await job_repository.get_job_by_id(accepted_offer.job_id)
        accepted_offers = await job_repository.list_offers_by_job(accepted_offer.job_id)
        accepted_offer_count = sum(
            1 for sibling in accepted_offers
            if sibling.status == "accepted"
        )

        if job is not None and accepted_offer_count == 1:
            await send_client_offer_selection_message(
                bot=message.bot,
                job=job,
                job_repository=job_repository,
                carrier_repository=carrier_repository,
            )

        await session.commit()

    await state.clear()

    if accepted_offer is not None:
        await message.answer(
            (
                f"{message_text}\n\n"
                f"Цена: {price_cents / 100:.2f} €"
                + (
                    f"\nКомментарий: {html.escape(carrier_note, quote=False)}"
                    if carrier_note
                    else ""
                )
            ),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("offer_decline_reason:"))
async def handle_offer_decline_reason(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    try:
        offer_id = int(parts[1])
    except ValueError:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    decline_reason = parts[2]
    if not is_valid_decline_reason(decline_reason):
        await callback.answer("Некорректная причина", show_alert=True)
        return

    telegram_user_id = callback.from_user.id
    job = None

    async with async_session_maker() as session:
        carrier_repository = CarrierRepository(session)
        job_repository = JobRepository(session)
        offer_service = JobOfferService(job_repository)

        carrier = await carrier_repository.get_carrier_by_telegram_user_id(
            telegram_user_id
        )
        offer = await job_repository.get_offer_by_id(offer_id)

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await callback.answer("Оффер не найден", show_alert=True)
            return

        try:
            declined_offer = await offer_service.decline_offer(
                offer_id,
                decline_reason=decline_reason,
            )
        except OfferAlreadyResolvedError:
            await callback.answer("Этот оффер уже обработан.", show_alert=True)
            await session.rollback()
            return

        job = await job_repository.get_job_by_id(declined_offer.job_id)
        if job is not None and job.status == "offered":
            sibling_offers = await job_repository.list_offers_by_job(job.id)
            has_open_offer = any(
                sibling.status in {"pending", "accepted"}
                for sibling in sibling_offers
            )

            if not has_open_offer:
                distribution = OfferDistributionService(
                    matching_service=JobMatchingService(
                        CarrierSearchService(carrier_repository)
                    ),
                    offer_service=offer_service,
                    job_repository=job_repository,
                )
                distribution_result = await distribution.create_offer_distribution_for_job(
                    job,
                    limit=5,
                    expires_in_minutes=60,
                )
                new_offers = distribution_result.offers
                if new_offers:
                    await send_job_offers_to_carriers(
                        bot=callback.bot,
                        job=job,
                        offers=new_offers,
                        job_repository=job_repository,
                        carrier_repository=carrier_repository,
                    )
                else:
                    await escalate_job_to_manual_review(
                        bot=callback.bot,
                        job=job,
                        job_repository=job_repository,
                        matching_reason=distribution_result.matching_reason,
                        matching_regions=distribution_result.matching_regions,
                    )

        await session.commit()

    if callback.message:
        await _delete_message_safely(callback.message)

    await callback.answer("Вы отказались от заказа.")


@router.callback_query(F.data.startswith("client_offer:"))
async def handle_client_offer_selection(callback: CallbackQuery) -> None:
    try:
        job_id, offer_id = parse_client_offer_selection_callback(callback.data or "")
    except ValueError:
        await callback.answer("Некорректная кнопка", show_alert=True)
        return

    telegram_user_id = callback.from_user.id

    carrier_telegram_user_id = None
    unselected_offer_message_refs: list[tuple[int | None, int | None]] = []

    async with async_session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        offer_service = JobOfferService(job_repository)

        job = await job_repository.get_job_by_id(job_id)

        if job is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return

        if job.client_telegram_user_id != telegram_user_id:
            await callback.answer("Эта кнопка не для вас.", show_alert=True)
            return

        offers_before_selection = await job_repository.list_offers_by_job(job_id)
        unselected_offer_message_refs = [
            (offer.carrier_message_chat_id, offer.carrier_message_id)
            for offer in offers_before_selection
            if offer.id != offer_id
            and offer.status in {"pending", "accepted"}
            and offer.carrier_message_chat_id is not None
            and offer.carrier_message_id is not None
        ]

        try:
            selected_offer = await offer_service.select_accepted_offer_for_client(
                job_id=job_id,
                offer_id=offer_id,
            )
        except ClientOfferSelectionError:
            await session.rollback()
            await callback.answer("Предложение уже недоступно.", show_alert=True)
            return

        selected_carrier = await carrier_repository.get_carrier_by_id(
            selected_offer.carrier_id
        )

        if selected_carrier is not None:
            carrier_telegram_user_id = selected_carrier.telegram_user_id

        await session.commit()

    for chat_id, message_id in unselected_offer_message_refs:
        await _delete_message_by_id_safely(
            callback.bot,
            chat_id=chat_id,
            message_id=message_id,
        )

    if callback.message:
        await callback.message.edit_text(
            build_client_assignment_confirmation_text(job_id, selected_carrier),
            reply_markup=build_client_reopen_assignment_keyboard(job_id),
            parse_mode="HTML",
        )

    await send_assignment_confirmation_requests(
        bot=callback.bot,
        job=job,
        carrier_telegram_user_id=carrier_telegram_user_id,
    )

    await callback.answer()
