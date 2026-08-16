import html
from datetime import UTC
from datetime import datetime

from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_elevator(value) -> str:
    if value is None:
        return "не указано"
    return "да" if value else "нет"


def _format_address(label: str, address) -> str:
    raw_text = address.raw_text if address else None
    normalized_address = getattr(address, "normalized_address", None) if address else None
    map_url = address.map_url if address else None
    floor = address.floor if address else None
    has_elevator = address.has_elevator if address else None
    address_details = getattr(address, "address_details", None) if address else None

    value = _safe(normalized_address or raw_text or "не указан")
    safe_label = _safe(label)
    details = f"\nЭтаж: {_safe(floor if floor is not None else 'не указан')}\nЛифт: {_format_elevator(has_elevator)}"
    if address_details:
        details += f"\nКвартира / доступ: {_safe(address_details)}"
    elif raw_text and normalized_address and raw_text.casefold() != normalized_address.casefold():
        details += f"\nВведено клиентом: {_safe(raw_text)}"

    if map_url and map_url != raw_text:
        return f"<b>{safe_label}</b>\n{value}\nКарта: {_safe(map_url)}{details}"
    return f"<b>{safe_label}</b>\n{value}{details}"


def _format_requested_date(value) -> str:
    if value is None:
        return "<b>Дата и время</b>\nне указаны"
    return "<b>Дата и время</b>\n" + _safe(value.strftime("%d.%m.%Y %H:%M"))


def _format_bool(value: bool) -> str:
    return "да" if value else "нет"


def _format_value(value, suffix: str) -> str:
    if value is None:
        return "не указано"
    return _safe(f"{value}{suffix}")


def _format_items(items) -> str:
    descriptions = [_safe(item.description) for item in items if item.description]
    return "; ".join(descriptions) if descriptions else "не указан"


def build_offer_text(job, items, pickup, dropoff) -> str:
    return (
        f"<b>Новая заявка #{job.id}</b>\n\n"
        f"{_format_requested_date(job.requested_date)}\n\n"
        f"{_format_address('Откуда', pickup)}\n\n"
        f"{_format_address('Куда', dropoff)}\n\n"
        "<b>Груз</b>\n"
        f"{_format_items(items)}\n\n"
        "<b>Параметры</b>\n"
        f"Объём: {_format_value(job.estimated_volume_m3, ' м³')}\n"
        f"Грузчики: {_format_value(job.required_loaders, '')}\n\n"
        "<b>Комментарий</b>\n"
        f"{_safe(job.comment or 'нет')}\n\n"
        "Примите или отклоните заявку."
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
        carrier = await carrier_repository.get_carrier_by_vehicle_id(
            offer.vehicle_id
        )

        if carrier is None or carrier.telegram_user_id is None:
            continue

        offer_text = build_offer_text(job, items, pickup, dropoff)
        keyboard = build_offer_keyboard(offer.id)

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
                text=f"Решение по заявке #{job.id}",
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

    return sent_count
