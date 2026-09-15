import html
import re
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from decimal import Decimal

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
from app.services.assignment_notifications import send_assignment_confirmation_requests
from app.services.client_offer_presentation import ClientOfferPresentationService
from app.bot.offer_keyboard import build_client_offer_selection_keyboard
from app.bot.offer_keyboard import build_offer_estimate_status_keyboard
from app.bot.offer_keyboard import build_offer_decline_reason_keyboard
from app.bot.offer_keyboard import build_offer_included_services_keyboard
from app.bot.offer_keyboard import build_offer_service_window_keyboard
from app.bot.offer_keyboard import build_offer_surcharges_keyboard
from app.bot.offer_keyboard import parse_client_offer_selection_callback
from app.bot.assignment_confirmation_keyboard import build_client_reopen_assignment_keyboard
from app.bot.carrier_locale import normalize_carrier_locale
from app.bot.offer_locale import offer_text as t
from app.bot.states.offer_response import OfferResponseStates

router = Router()

_offer_price_input_re = re.compile(r"^\d+(?:[.,]\d{1,2})?$")
_offer_price_only_re = re.compile(
    r"^(?:€\s*)?(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur(?:os?)?|euro|евро)?$",
    re.IGNORECASE,
)
_offer_text_field_max_length = 500
_estimate_status_aliases = {
    "final": "final",
    "definitivo": "final",
    "definitiva": "final",
    "окончательная": "final",
    "окончательный": "final",
    "estimate": "estimate",
    "estimated": "estimate",
    "preliminary": "estimate",
    "estimativa": "estimate",
    "estimado": "estimate",
    "preliminar": "estimate",
    "предварительная": "estimate",
    "предварительный": "estimate",
}


@dataclass(frozen=True)
class ParsedOfferInput:
    price_cents: int
    included_services: str
    possible_surcharges: str
    service_window: str
    estimate_status: str
    carrier_note: str | None


def _parse_offer_price_input(text: str) -> ParsedOfferInput:
    lines = [line.strip() for line in text.strip().splitlines()]
    if len(lines) < 5 or any(not line for line in lines[:5]):
        raise ValueError("incomplete offer terms")

    price_text = lines[0].replace(",", ".")
    if _offer_price_input_re.fullmatch(lines[0]) is None:
        raise ValueError("invalid offer price")

    price = Decimal(price_text)
    if price <= 0:
        raise ValueError("invalid offer price")

    included_services = lines[1]
    possible_surcharges = lines[2]
    service_window = lines[3]
    estimate_status = _estimate_status_aliases.get(lines[4].casefold())
    if estimate_status is None:
        raise ValueError("invalid estimate status")
    if len(service_window) > 255:
        raise ValueError("service window is too long")

    carrier_note = "\n".join(line for line in lines[5:] if line) or None
    return ParsedOfferInput(
        price_cents=int(price * 100),
        included_services=included_services,
        possible_surcharges=possible_surcharges,
        service_window=service_window,
        estimate_status=estimate_status,
        carrier_note=carrier_note,
    )


def _parse_offer_price_only(text: str) -> int:
    match = _offer_price_only_re.fullmatch(text.strip())
    if match is None:
        raise ValueError("invalid offer price")

    price = Decimal(match.group(1).replace(",", "."))
    if price <= 0:
        raise ValueError("invalid offer price")

    return int(price * 100)


def _parse_required_offer_text(text: str, *, max_length: int) -> str:
    value = text.strip()
    if not value or len(value) > max_length:
        raise ValueError("invalid offer term")
    return value


def _parse_estimate_status_input(text: str) -> tuple[str, str | None]:
    value = text.strip()
    folded = value.casefold()
    for alias in sorted(_estimate_status_aliases, key=len, reverse=True):
        if not folded.startswith(alias):
            continue
        if len(value) > len(alias) and value[len(alias)] not in " \t\n,;:-—–":
            continue

        carrier_note = value[len(alias):].lstrip(" \t\n,;:-—–") or None
        if carrier_note and len(carrier_note) > _offer_text_field_max_length:
            raise ValueError("carrier note is too long")
        return _estimate_status_aliases[alias], carrier_note

    raise ValueError("invalid estimate status")


def _offer_locale_from_data(data: dict, fallback: str | None = None) -> str:
    return normalize_carrier_locale(data.get("offer_price_locale") or fallback)


def _offer_id_from_data(data: dict) -> int | None:
    offer_id = data.get("offer_price_offer_id")
    if offer_id is None:
        return None
    return int(offer_id)


async def _set_offer_step(
    *,
    message: Message,
    state: FSMContext,
    offer_id: int,
    locale: str,
    next_state,
    prompt_key: str,
    reply_markup=None,
) -> None:
    await state.set_state(next_state)
    prompt_message = await message.answer(
        t(locale, prompt_key),
        reply_markup=reply_markup,
    )
    await state.update_data(
        offer_step_prompt_chat_id=prompt_message.chat.id if reply_markup else None,
        offer_step_prompt_message_id=(
            prompt_message.message_id if reply_markup else None
        ),
    )


async def _clear_offer_step_keyboard(bot, data: dict) -> None:
    chat_id = data.get("offer_step_prompt_chat_id")
    message_id = data.get("offer_step_prompt_message_id")
    if chat_id is None or message_id is None:
        return

    try:
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=None,
        )
    except TelegramBadRequest:
        return


async def _prompt_offer_price(
    callback: CallbackQuery,
    state: FSMContext,
    offer_id: int,
    locale: str | None = None,
) -> None:
    if callback.message is None:
        await callback.answer(t(locale, "request_unknown"), show_alert=True)
        return

    await state.clear()
    await state.update_data(
        offer_price_offer_id=offer_id,
        offer_price_message_chat_id=callback.message.chat.id,
        offer_price_message_id=callback.message.message_id,
        offer_price_locale=normalize_carrier_locale(locale),
    )
    await state.set_state(OfferResponseStates.price)

    await callback.message.answer(
        t(locale, "price_prompt")
    )
    await callback.answer(t(locale, "price_reply"))


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


def _format_client_offer_value(value, suffix: str = "", locale: str | None = None) -> str:
    if value is None:
        return t(locale, "not_provided")
    return html.escape(f"{value}{suffix}", quote=False)


def build_client_offer_selection_text(
    job_id: int,
    offers,
    locale: str | None = None,
) -> str:
    lines = [
        f"<b>{t(locale, 'client_offers_title', job_id=job_id)}</b>",
        "",
        t(locale, "choose_offer"),
    ]

    for index, offer in enumerate(offers, start=1):
        lines.extend(
            [
                "",
                f"<b>{t(locale, 'offer_label', index=index)}</b>",
                f"{t(locale, 'company')}: {html.escape(offer.company_name, quote=False)}",
                f"{t(locale, 'vehicle')}: {html.escape(offer.vehicle_type, quote=False)}",
                f"{t(locale, 'payload')}: {_format_client_offer_value(offer.payload_kg, ' kg', locale)}",
                f"{t(locale, 'volume')}: {_format_client_offer_value(offer.volume_m3, ' m³', locale)}",
                f"{t(locale, 'loaders')}: {_format_client_offer_value(offer.max_loaders, locale=locale)}",
            ]
        )

        if offer.price_cents is not None:
            lines.append(f"{t(locale, 'price')}: {offer.price_cents / 100:.2f} €")

        lines.extend(
            [
                f"{t(locale, 'included_services')}: "
                f"{_format_client_offer_value(offer.included_services, locale=locale)}",
                f"{t(locale, 'possible_surcharges')}: "
                f"{_format_client_offer_value(offer.possible_surcharges, locale=locale)}",
                f"{t(locale, 'service_window')}: "
                f"{_format_client_offer_value(offer.service_window, locale=locale)}",
                f"{t(locale, 'estimate_status')}: "
                + (
                    t(locale, f"estimate_{offer.estimate_status}")
                    if offer.estimate_status in {"final", "estimate"}
                    else t(locale, "not_provided")
                ),
            ]
        )

        if offer.carrier_note:
            lines.append(
                f"{t(locale, 'note')}: {html.escape(offer.carrier_note, quote=False)}"
            )

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
        text=build_client_offer_selection_text(job.id, views, job.source_locale),
        reply_markup=build_client_offer_selection_keyboard(views, job.source_locale),
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


@router.callback_query(F.data.startswith("offer:"))
async def handle_offer_response(callback: CallbackQuery, state: FSMContext) -> None:
    locale = normalize_carrier_locale(callback.from_user.language_code)
    try:
        action, offer_id = parse_offer_callback(callback.data or "")
    except ValueError:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
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
        if carrier is not None:
            locale = normalize_carrier_locale(carrier.preferred_locale or locale)

        offer = await job_repository.get_offer_by_id(offer_id)

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await callback.answer(t(locale, "offer_not_found"), show_alert=True)
            return

        if action == "accept":
            if offer.status != "pending":
                await callback.answer(t(locale, "offer_resolved"), show_alert=True)
                return

            await _prompt_offer_price(callback, state, offer_id, locale=locale)
            return
        else:
            if callback.message:
                await callback.message.edit_reply_markup(
                    reply_markup=build_offer_decline_reason_keyboard(
                        offer_id,
                        locale=locale,
                    ),
                )
            await callback.answer(t(locale, "decline_reason_prompt"))
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

async def _submit_offer_response(
    *,
    message: Message,
    state: FSMContext,
    parsed_offer: ParsedOfferInput,
    telegram_user_id: int,
) -> bool:
    data = await state.get_data()
    locale = _offer_locale_from_data(data)
    offer_id = _offer_id_from_data(data)
    offer_message_chat_id = data.get("offer_price_message_chat_id")
    offer_message_id = data.get("offer_price_message_id")

    if offer_id is None:
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return False

    job = None
    accepted_offer = None
    message_text = t(locale, "response_sent")

    async with async_session_maker() as session:
        carrier_repository = CarrierRepository(session)
        job_repository = JobRepository(session)
        offer_service = JobOfferService(job_repository)

        carrier = await carrier_repository.get_carrier_by_telegram_user_id(
            telegram_user_id
        )
        if carrier is not None:
            locale = normalize_carrier_locale(carrier.preferred_locale or locale)
            message_text = t(locale, "response_sent")
        offer = await job_repository.get_offer_by_id(int(offer_id))

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await session.rollback()
            await state.clear()
            await message.answer(t(locale, "offer_not_found"))
            return False

        if offer.status != "pending":
            await session.rollback()
            await state.clear()
            await message.answer(t(locale, "offer_resolved"))
            return False

        try:
            await job_repository.update_offer_terms(
                offer_id=offer.id,
                price_cents=parsed_offer.price_cents,
                included_services=parsed_offer.included_services,
                possible_surcharges=parsed_offer.possible_surcharges,
                service_window=parsed_offer.service_window,
                estimate_status=parsed_offer.estimate_status,
                carrier_note=parsed_offer.carrier_note,
                updated_at=datetime.now(UTC),
            )
            accepted_offer = await offer_service.accept_offer_without_assignment(offer.id)
        except OfferAlreadyResolvedError:
            await session.rollback()
            await state.clear()
            await message.answer(t(locale, "offer_resolved"))
            return False
        except JobAlreadyAssignedError:
            await session.rollback()
            await state.clear()
            await message.answer(t(locale, "request_closed"))
            return False

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
        if offer_message_chat_id is not None and offer_message_id is not None:
            try:
                await message.bot.edit_message_reply_markup(
                    chat_id=offer_message_chat_id,
                    message_id=offer_message_id,
                    reply_markup=None,
                )
            except TelegramBadRequest:
                pass

        await message.answer(
            (
                f"{message_text}\n\n"
                f"{t(locale, 'price')}: {parsed_offer.price_cents / 100:.2f} €\n"
                f"{t(locale, 'included_services')}: "
                f"{html.escape(parsed_offer.included_services, quote=False)}\n"
                f"{t(locale, 'possible_surcharges')}: "
                f"{html.escape(parsed_offer.possible_surcharges, quote=False)}\n"
                f"{t(locale, 'service_window')}: "
                f"{html.escape(parsed_offer.service_window, quote=False)}\n"
                f"{t(locale, 'estimate_status')}: "
                f"{t(locale, 'estimate_' + parsed_offer.estimate_status)}"
                + (
                    f"\n{t(locale, 'note')}: "
                    f"{html.escape(parsed_offer.carrier_note, quote=False)}"
                    if parsed_offer.carrier_note
                    else ""
                )
            ),
            parse_mode="HTML",
        )

    return True


def _build_conversational_offer(
    data: dict,
    *,
    estimate_status: str,
    carrier_note: str | None = None,
) -> ParsedOfferInput:
    if estimate_status not in {"final", "estimate"}:
        raise ValueError("invalid estimate status")

    price_cents = int(data["offer_price_cents"])
    included_services = _parse_required_offer_text(
        str(data["offer_included_services"]),
        max_length=_offer_text_field_max_length,
    )
    possible_surcharges = _parse_required_offer_text(
        str(data["offer_possible_surcharges"]),
        max_length=_offer_text_field_max_length,
    )
    service_window = _parse_required_offer_text(
        str(data["offer_service_window"]),
        max_length=255,
    )

    return ParsedOfferInput(
        price_cents=price_cents,
        included_services=included_services,
        possible_surcharges=possible_surcharges,
        service_window=service_window,
        estimate_status=estimate_status,
        carrier_note=carrier_note,
    )


async def _prompt_included_services(
    message: Message,
    state: FSMContext,
    offer_id: int,
    locale: str,
) -> None:
    await _set_offer_step(
        message=message,
        state=state,
        offer_id=offer_id,
        locale=locale,
        next_state=OfferResponseStates.included_services,
        prompt_key="included_services_prompt",
        reply_markup=build_offer_included_services_keyboard(offer_id, locale),
    )


async def _prompt_possible_surcharges(
    message: Message,
    state: FSMContext,
    offer_id: int,
    locale: str,
) -> None:
    await _set_offer_step(
        message=message,
        state=state,
        offer_id=offer_id,
        locale=locale,
        next_state=OfferResponseStates.possible_surcharges,
        prompt_key="possible_surcharges_prompt",
        reply_markup=build_offer_surcharges_keyboard(offer_id, locale),
    )


async def _prompt_service_window(
    message: Message,
    state: FSMContext,
    offer_id: int,
    locale: str,
) -> None:
    await _set_offer_step(
        message=message,
        state=state,
        offer_id=offer_id,
        locale=locale,
        next_state=OfferResponseStates.service_window,
        prompt_key="service_window_prompt",
        reply_markup=build_offer_service_window_keyboard(offer_id, locale),
    )


async def _prompt_estimate_status(
    message: Message,
    state: FSMContext,
    offer_id: int,
    locale: str,
) -> None:
    await _set_offer_step(
        message=message,
        state=state,
        offer_id=offer_id,
        locale=locale,
        next_state=OfferResponseStates.estimate_status,
        prompt_key="estimate_status_prompt",
        reply_markup=build_offer_estimate_status_keyboard(offer_id, locale),
    )


@router.message(OfferResponseStates.price)
async def handle_offer_price_input(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(
        data,
        message.from_user.language_code if message.from_user else None,
    )
    offer_id = _offer_id_from_data(data)

    if offer_id is None:
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return

    payload = (message.text or "").strip()

    try:
        parsed_offer = _parse_offer_price_input(payload)
    except ValueError:
        parsed_offer = None

    telegram_user_id = message.from_user.id if message.from_user else None
    if telegram_user_id is None:
        await state.clear()
        await message.answer(t(locale, "carrier_unknown"))
        return

    if parsed_offer is not None:
        await _submit_offer_response(
            message=message,
            state=state,
            parsed_offer=parsed_offer,
            telegram_user_id=telegram_user_id,
        )
        return

    try:
        price_cents = _parse_offer_price_only(payload)
    except ValueError:
        await message.answer(t(locale, "price_input_invalid"))
        return

    await state.update_data(offer_price_cents=price_cents)
    await _prompt_included_services(message, state, offer_id, locale)


@router.message(OfferResponseStates.included_services)
async def handle_offer_included_services_input(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(
        data,
        message.from_user.language_code if message.from_user else None,
    )
    offer_id = _offer_id_from_data(data)
    if offer_id is None:
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return

    try:
        included_services = _parse_required_offer_text(
            message.text or "",
            max_length=_offer_text_field_max_length,
        )
    except ValueError:
        await message.answer(t(locale, "offer_step_invalid"))
        return

    await _clear_offer_step_keyboard(message.bot, data)
    await state.update_data(offer_included_services=included_services)
    await _prompt_possible_surcharges(message, state, offer_id, locale)


@router.message(OfferResponseStates.possible_surcharges)
async def handle_offer_possible_surcharges_input(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(
        data,
        message.from_user.language_code if message.from_user else None,
    )
    offer_id = _offer_id_from_data(data)
    if offer_id is None:
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return

    try:
        possible_surcharges = _parse_required_offer_text(
            message.text or "",
            max_length=_offer_text_field_max_length,
        )
    except ValueError:
        await message.answer(t(locale, "offer_step_invalid"))
        return

    await _clear_offer_step_keyboard(message.bot, data)
    await state.update_data(offer_possible_surcharges=possible_surcharges)
    await _prompt_service_window(message, state, offer_id, locale)


@router.message(OfferResponseStates.service_window)
async def handle_offer_service_window_input(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(
        data,
        message.from_user.language_code if message.from_user else None,
    )
    offer_id = _offer_id_from_data(data)
    if offer_id is None:
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return

    try:
        service_window = _parse_required_offer_text(
            message.text or "",
            max_length=255,
        )
    except ValueError:
        await message.answer(t(locale, "offer_step_invalid"))
        return

    await _clear_offer_step_keyboard(message.bot, data)
    await state.update_data(offer_service_window=service_window)
    await _prompt_estimate_status(message, state, offer_id, locale)


@router.message(OfferResponseStates.estimate_status)
async def handle_offer_estimate_status_input(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(
        data,
        message.from_user.language_code if message.from_user else None,
    )
    try:
        estimate_status, carrier_note = _parse_estimate_status_input(
            message.text or ""
        )
    except ValueError:
        await message.answer(t(locale, "offer_step_invalid"))
        return

    telegram_user_id = message.from_user.id if message.from_user else None
    if telegram_user_id is None:
        await state.clear()
        await message.answer(t(locale, "carrier_unknown"))
        return

    try:
        parsed_offer = _build_conversational_offer(
            data,
            estimate_status=estimate_status,
            carrier_note=carrier_note,
        )
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await message.answer(t(locale, "request_unknown"))
        return

    await _clear_offer_step_keyboard(message.bot, data)
    await _submit_offer_response(
        message=message,
        state=state,
        parsed_offer=parsed_offer,
        telegram_user_id=telegram_user_id,
    )


@router.callback_query(F.data.startswith("offer_terms:"))
async def handle_offer_terms_shortcut(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = _offer_locale_from_data(data, callback.from_user.language_code)
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
        return

    field, offer_id_text, value = parts[1:]
    try:
        offer_id = int(offer_id_text)
    except ValueError:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
        return

    expected_states = {
        "included": OfferResponseStates.included_services.state,
        "surcharges": OfferResponseStates.possible_surcharges.state,
        "window": OfferResponseStates.service_window.state,
        "status": OfferResponseStates.estimate_status.state,
    }
    current_state = await state.get_state()
    if (
        field not in expected_states
        or current_state != expected_states[field]
        or _offer_id_from_data(data) != offer_id
        or callback.message is None
    ):
        await callback.answer(t(locale, "offer_step_expired"), show_alert=True)
        return

    allowed_values = {
        "included": {"requested"},
        "surcharges": {"none"},
        "window": {"requested"},
        "status": {"final", "estimate"},
    }
    if value not in allowed_values[field]:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass
    await callback.answer()

    if field == "included":
        await state.update_data(
            offer_included_services=t(
                locale,
                "included_services_as_requested_value",
            )
        )
        await _prompt_possible_surcharges(
            callback.message,
            state,
            offer_id,
            locale,
        )
        return

    if field == "surcharges":
        await state.update_data(
            offer_possible_surcharges=t(
                locale,
                "possible_surcharges_none_value",
            )
        )
        await _prompt_service_window(
            callback.message,
            state,
            offer_id,
            locale,
        )
        return

    if field == "window":
        await state.update_data(
            offer_service_window=t(
                locale,
                "service_window_as_requested_value",
            )
        )
        await _prompt_estimate_status(
            callback.message,
            state,
            offer_id,
            locale,
        )
        return

    refreshed_data = await state.get_data()
    try:
        parsed_offer = _build_conversational_offer(
            refreshed_data,
            estimate_status=value,
        )
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await callback.message.answer(t(locale, "request_unknown"))
        return

    await _submit_offer_response(
        message=callback.message,
        state=state,
        parsed_offer=parsed_offer,
        telegram_user_id=callback.from_user.id,
    )


@router.callback_query(F.data.startswith("offer_decline_reason:"))
async def handle_offer_decline_reason(callback: CallbackQuery) -> None:
    locale = normalize_carrier_locale(callback.from_user.language_code)
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
        return

    try:
        offer_id = int(parts[1])
    except ValueError:
        await callback.answer(t(locale, "invalid_button"), show_alert=True)
        return

    decline_reason = parts[2]
    if not is_valid_decline_reason(decline_reason):
        await callback.answer(t(locale, "invalid_reason"), show_alert=True)
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
        if carrier is not None:
            locale = normalize_carrier_locale(carrier.preferred_locale or locale)
        offer = await job_repository.get_offer_by_id(offer_id)

        if carrier is None or offer is None or offer.carrier_id != carrier.id:
            await callback.answer(t(locale, "offer_not_found"), show_alert=True)
            return

        try:
            declined_offer = await offer_service.decline_offer(
                offer_id,
                decline_reason=decline_reason,
            )
        except OfferAlreadyResolvedError:
            await callback.answer(t(locale, "offer_resolved"), show_alert=True)
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

    await callback.answer(t(locale, "declined_done"))


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
        carrier_locale=(
            selected_carrier.preferred_locale
            if selected_carrier is not None
            else None
        ),
    )

    await callback.answer()
