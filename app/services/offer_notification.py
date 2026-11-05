import html
import logging
from datetime import UTC
from datetime import datetime

from aiogram.exceptions import TelegramForbiddenError

from app.bot.offer_locale import offer_text as t
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_elevator(value, locale: str | None) -> str:
    if value is None:
        return t(locale, "not_provided")
    return t(locale, "yes") if value else t(locale, "no")


def _format_address(label_key: str, address, locale: str | None) -> str:
    raw_text = address.raw_text if address else None
    normalized_address = getattr(address, "normalized_address", None) if address else None
    map_url = address.map_url if address else None
    floor = address.floor if address else None
    has_elevator = address.has_elevator if address else None
    address_details = getattr(address, "address_details", None) if address else None

    value = _safe(normalized_address or raw_text or t(locale, "not_provided"))
    safe_label = _safe(t(locale, label_key))
    floor_value = floor if floor is not None else t(locale, "not_provided")
    details = (
        f"\n{t(locale, 'floor')}: {_safe(floor_value)}"
        f"\n{t(locale, 'elevator')}: {_format_elevator(has_elevator, locale)}"
    )
    if address_details:
        details += f"\n{t(locale, 'access')}: {_safe(address_details)}"
    elif raw_text and normalized_address and raw_text.casefold() != normalized_address.casefold():
        details += f"\n{t(locale, 'client_input')}: {_safe(raw_text)}"

    if map_url and map_url != raw_text:
        return f"<b>{safe_label}</b>\n{value}\n{t(locale, 'map')}: {_safe(map_url)}{details}"
    return f"<b>{safe_label}</b>\n{value}{details}"


def _format_requested_date(value, locale: str | None) -> str:
    if value is None:
        return f"<b>{t(locale, 'date_time')}</b>\n{t(locale, 'not_provided_plural')}"
    return f"<b>{t(locale, 'date_time')}</b>\n" + _safe(value.strftime("%d.%m.%Y %H:%M"))


def _format_value(value, suffix: str, locale: str | None) -> str:
    if value is None:
        return t(locale, "not_provided")
    return _safe(f"{value}{suffix}")


def _format_items(items, locale: str | None) -> str:
    descriptions = [_safe(item.description) for item in items if item.description]
    return "; ".join(descriptions) if descriptions else t(locale, "not_provided")


def build_offer_text(job, items, pickup, dropoff, locale: str | None = None) -> str:
    return (
        f"<b>{t(locale, 'new_request', job_id=job.id)}</b>\n\n"
        f"{_format_requested_date(job.requested_date, locale)}\n\n"
        f"{_format_address('pickup', pickup, locale)}\n\n"
        f"{_format_address('dropoff', dropoff, locale)}\n\n"
        f"<b>{t(locale, 'cargo')}</b>\n"
        f"{_format_items(items, locale)}\n\n"
        f"<b>{t(locale, 'parameters')}</b>\n"
        f"{t(locale, 'volume')}: {_format_value(job.estimated_volume_m3, ' м³', locale)}\n"
        f"{t(locale, 'loaders')}: {_format_value(job.required_loaders, '', locale)}\n\n"
        f"<b>{t(locale, 'comment')}</b>\n"
        f"{_safe(job.comment or t(locale, 'no_comment'))}\n\n"
        f"{t(locale, 'decision_prompt')}"
    )


async def send_job_offers_to_carriers(
    *,
    bot,
    job,
    offers,
    job_repository: JobRepository,
    carrier_repository: CarrierRepository,
) -> int:
    from aiogram.types import InputMediaPhoto
    from aiogram.types import InputMediaVideo

    from app.bot.offer_keyboard import build_offer_keyboard

    media_items = await job_repository.list_media_by_job(job.id)
    items = await job_repository.list_items_by_job(job.id)
    addresses = await job_repository.list_addresses_by_job(job.id)
    pickup = next((item for item in addresses if item.kind == "pickup"), None)
    dropoff = next((item for item in addresses if item.kind == "dropoff"), None)

    sent_count = 0

    for offer in offers:
        try:
            carrier = await carrier_repository.get_carrier_by_vehicle_id(
                offer.vehicle_id
            )

            if carrier is None or carrier.telegram_user_id is None:
                continue

            locale = carrier.preferred_locale
            offer_text = build_offer_text(job, items, pickup, dropoff, locale=locale)
            keyboard = build_offer_keyboard(offer.id, locale=locale)

            sent_offer_message = None

            if not media_items:
                sent_offer_message = await bot.send_message(
                    chat_id=carrier.telegram_user_id,
                    text=offer_text,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            elif len(media_items) == 1:
                media = media_items[0]
                if media.media_type == "photo":
                    sent_offer_message = await bot.send_photo(
                        chat_id=carrier.telegram_user_id,
                        photo=media.telegram_file_id,
                        caption=offer_text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
                elif media.media_type == "video":
                    if len(offer_text) > 1024:
                        await bot.send_video(
                            chat_id=carrier.telegram_user_id,
                            video=media.telegram_file_id,
                        )
                        sent_offer_message = await bot.send_message(
                            chat_id=carrier.telegram_user_id,
                            text=offer_text,
                            reply_markup=keyboard,
                            parse_mode="HTML",
                        )
                    else:
                        sent_offer_message = await bot.send_video(
                            chat_id=carrier.telegram_user_id,
                            video=media.telegram_file_id,
                            caption=offer_text,
                            reply_markup=keyboard,
                            parse_mode="HTML",
                        )
                else:
                    sent_offer_message = await bot.send_message(
                        chat_id=carrier.telegram_user_id,
                        text=offer_text,
                        reply_markup=keyboard,
                        parse_mode="HTML",
                    )
            else:
                album = []
                for index, media in enumerate(media_items[:10]):
                    caption = offer_text if index == 0 else None
                    if media.media_type == "photo":
                        album.append(
                            InputMediaPhoto(
                                media=media.telegram_file_id,
                                caption=caption,
                                parse_mode="HTML",
                            )
                        )
                    elif media.media_type == "video":
                        album.append(
                            InputMediaVideo(
                                media=media.telegram_file_id,
                                caption=caption,
                                parse_mode="HTML",
                            )
                        )

                if album:
                    await bot.send_media_group(
                        chat_id=carrier.telegram_user_id,
                        media=album,
                    )

                sent_offer_message = await bot.send_message(
                    chat_id=carrier.telegram_user_id,
                    text=t(locale, "decision", job_id=job.id),
                    reply_markup=keyboard,
                )

            if sent_offer_message is not None:
                await job_repository.update_offer_carrier_message(
                    offer_id=offer.id,
                    chat_id=sent_offer_message.chat.id,
                    message_id=sent_offer_message.message_id,
                    updated_at=datetime.now(UTC),
                )

            sent_count += 1

        except TelegramForbiddenError:
            logging.getLogger(__name__).warning(
                "Telegram blocked: job=%s offer=%s carrier=%s",
                job.id, offer.id, offer.carrier_id,
            )
            continue

    return sent_count
