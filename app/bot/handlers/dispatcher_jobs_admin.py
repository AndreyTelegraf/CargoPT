import html
from datetime import UTC
from datetime import datetime

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from sqlalchemy import text

from app.bot.handlers.carrier_invite_admin import ADMIN_TELEGRAM_USER_IDS
from app.db.session import async_session_maker
from app.domain.job_decline_reason import get_decline_reason_label
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService
from app.services.job_offer import JobOfferService
from app.services.offer_distribution import OfferDistributionService
from app.services.offer_notification import send_job_offers_to_carriers

router = Router()


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_dt(value) -> str:
    if value is None:
        return "—"
    return _safe(value.strftime("%d.%m.%Y %H:%M"))


STATUS_LABELS = {
    "draft": "черновик",
    "ready_for_matching": "готова к поиску",
    "matching": "поиск перевозчика",
    "offered": "отправлена перевозчикам",
    "unmatched": "перевозчик не найден",
    "no_carriers_found": "нет подходящих перевозчиков",
    "offers_exhausted": "все перевозчики отказались",
    "expired_without_response": "нет ответов от перевозчиков",
    "manual_review_required": "требует ручного контроля",
    "assigned_pending_confirmation": "ожидает подтверждения сделки",
    "assigned": "перевозчик назначен",
    "in_progress": "в работе",
    "completed": "завершена",
    "cancelled": "отменена",
}


def _format_status(value: str) -> str:
    return STATUS_LABELS.get(value, value)


def _format_job_line(job) -> str:
    client = job.client_telegram_username or str(job.client_telegram_user_id)
    line = (
        f"<b>#{job.id}</b> — {_safe(_format_status(job.status))} — @{_safe(client)}\n"
        f"Дата: {_format_dt(job.requested_date)}\n"
        f"Назначена: {_format_dt(job.assigned_at)} | "
        f"Старт: {_format_dt(job.started_at)} | "
        f"Завершена: {_format_dt(job.completed_at)} | "
        f"Отменена: {_format_dt(job.cancelled_at)}"
    )

    offers_count = getattr(job, "offers_count", None)
    if offers_count is not None:
        line += f"\nОфферов: {_safe(offers_count)}"

    attention_reason = getattr(job, "attention_reason", None)
    if attention_reason:
        line += f"\nПричина: {_safe(get_decline_reason_label(attention_reason))}"

    return line


async def _send_jobs_list(
    *,
    message: Message,
    title: str,
    empty_text: str,
    jobs,
) -> None:
    if not jobs:
        await message.answer(empty_text)
        return

    text = title + "\n\n" + "\n\n".join(
        _format_job_line(job) for job in jobs
    )

    await message.answer(text, parse_mode="HTML")

def _format_status_counts(rows) -> str:
    if not rows:
        return "—"
    return "\n".join(
        f"{_safe(_format_status(row['status']))}: {_safe(row['count'])}"
        for row in rows
    )


def _format_offer_counts(rows) -> str:
    if not rows:
        return "—"
    return "\n".join(
        f"{_safe(row['status'])}: {_safe(row['count'])}"
        for row in rows
    )


def _format_report_job_rows(rows) -> str:
    if not rows:
        return "—"

    lines = []
    for row in rows:
        client = row["client_telegram_username"] or str(row["client_telegram_user_id"])
        line = (
            f"<b>#{_safe(row['id'])}</b> — {_safe(_format_status(row['status']))} — @{_safe(client)}\n"
            f"Офферов: {_safe(row['offers'])} | "
            f"accepted: {_safe(row['accepted'])} | "
            f"declined: {_safe(row['declined'])} | "
            f"expired: {_safe(row['expired'])} | "
            f"pending: {_safe(row['pending'])}"
        )
        if row["latest_reason"]:
            line += f"\nПричина: {_safe(get_decline_reason_label(row['latest_reason']))}"
        lines.append(line)

    return "\n\n".join(lines)


def _format_optional(value) -> str:
    if value is None or value == "":
        return "—"
    return _safe(value)


def _format_bool_admin(value) -> str:
    if value is True:
        return "да"
    if value is False:
        return "нет"
    return "—"


def _format_address_line(address) -> str:
    parts = [
        f"<b>{_safe(address.kind)}</b>: {_safe(address.raw_text)}",
    ]

    details = []
    if address.normalized_address:
        details.append(f"нормализовано: {_safe(address.normalized_address)}")
    if address.city:
        details.append(f"город: {_safe(address.city)}")
    if address.postal_code:
        details.append(f"индекс: {_safe(address.postal_code)}")
    if address.floor is not None:
        details.append(f"этаж: {_safe(address.floor)}")
    if address.has_elevator is not None:
        details.append(f"лифт: {_format_bool_admin(address.has_elevator)}")
    if address.map_url:
        details.append(f"карта: {_safe(address.map_url)}")

    if details:
        parts.append(" · ".join(details))

    return "\n".join(parts)


def _format_item_line(item) -> str:
    details = []
    if item.quantity is not None:
        details.append(f"кол-во: {_safe(item.quantity)}")
    if item.estimated_weight_kg is not None:
        details.append(f"вес: {_safe(item.estimated_weight_kg)} кг")
    if item.estimated_volume_m3 is not None:
        details.append(f"объём: {_safe(item.estimated_volume_m3)} м³")

    suffix = f" ({', '.join(details)})" if details else ""
    return f"• {_safe(item.description)}{suffix}"


def _format_offer_summary(offers) -> str:
    statuses = {
        "sent": len(offers),
        "pending": sum(1 for offer in offers if offer.status == "pending"),
        "accepted": sum(1 for offer in offers if offer.status == "accepted"),
        "declined": sum(1 for offer in offers if offer.status == "declined"),
        "expired": sum(1 for offer in offers if offer.status == "expired"),
        "cancelled": sum(1 for offer in offers if offer.status == "cancelled"),
    }

    return (
        f"отправлено — {_safe(statuses['sent'])}\n"
        f"pending — {_safe(statuses['pending'])}\n"
        f"accepted — {_safe(statuses['accepted'])}\n"
        f"declined — {_safe(statuses['declined'])}\n"
        f"expired — {_safe(statuses['expired'])}\n"
        f"cancelled — {_safe(statuses['cancelled'])}"
    )


def _format_latest_decline_reason(offers) -> str:
    reasons = [
        offer.decline_reason
        for offer in reversed(offers)
        if getattr(offer, "decline_reason", None)
    ]
    if not reasons:
        return "—"
    return _safe(get_decline_reason_label(reasons[0]))


def _build_job_card_text(*, job, addresses, items, offers) -> str:
    client = job.client_telegram_username or str(job.client_telegram_user_id or "—")
    client_line = f"@{_safe(client)}" if client != "—" else "—"

    address_text = "\n\n".join(_format_address_line(address) for address in addresses) or "—"
    item_text = "\n".join(_format_item_line(item) for item in items) or "—"

    return (
        f"<b>Заявка #{_safe(job.id)}</b>\n\n"
        f"<b>Статус</b>\n{_safe(_format_status(job.status))} ({_safe(job.status)})\n\n"
        f"<b>Клиент</b>\n"
        f"Telegram: {client_line}\n"
        f"ID: {_format_optional(job.client_telegram_user_id)}\n"
        f"Имя: {_format_optional(job.customer_name)}\n"
        f"Телефон: {_format_optional(job.client_phone)}\n"
        f"WhatsApp: {_format_optional(job.client_whatsapp)}\n"
        f"Email: {_format_optional(job.customer_email)}\n"
        f"Предпочтительный контакт: {_format_optional(job.preferred_contact)}\n\n"
        f"<b>Дата</b>\n"
        f"Желаемая: {_format_dt(job.requested_date)}\n"
        f"Создана: {_format_dt(job.created_at)}\n"
        f"Обновлена: {_format_dt(job.updated_at)}\n\n"
        f"<b>Адреса</b>\n{address_text}\n\n"
        f"<b>Груз</b>\n{item_text}\n\n"
        f"<b>Параметры</b>\n"
        f"Грузчики: {_format_optional(job.required_loaders)}\n"
        f"Вес: {_format_optional(job.estimated_payload_kg)} кг\n"
        f"Объём: {_format_optional(job.estimated_volume_m3)} м³\n"
        f"Сборка: {_format_bool_admin(job.needs_assembly)}\n"
        f"Упаковка: {_format_bool_admin(job.needs_packing)}\n"
        f"Гидроборт: {_format_bool_admin(job.needs_tail_lift)}\n"
        f"Кран: {_format_bool_admin(job.needs_crane)}\n"
        f"Мобильный лифт: {_format_bool_admin(job.needs_mobile_lift)}\n\n"
        f"<b>Офферы</b>\n{_format_offer_summary(offers)}\n"
        f"Последняя причина отказа: {_format_latest_decline_reason(offers)}\n\n"
        f"<b>Комментарий</b>\n{_format_optional(job.comment)}\n\n"
        f"<b>Источник</b>\n"
        f"{_format_optional(job.source)} / {_format_optional(job.source_locale)}\n"
        f"UTM: {_format_optional(job.utm_source)} / {_format_optional(job.utm_campaign)}\n"
        f"Landing: {_format_optional(job.landing_version)}"
    )


def _normalize_report_datetime(value: str, *, is_end: bool = False) -> str:
    raw = value.strip()
    if len(raw) == 10:
        return raw + (" 23:59:59" if is_end else " 00:00:00")
    if len(raw) == 16:
        return raw + ":00"
    return raw


def _parse_jobs_report_period(text: str) -> tuple[str, str | None]:
    parts = text.split()[1:]

    if not parts:
        return "2026-06-25 00:00:00", None

    if len(parts) == 1:
        return _normalize_report_datetime(parts[0]), None

    if len(parts) == 2:
        return (
            _normalize_report_datetime(parts[0]),
            _normalize_report_datetime(parts[1], is_end=True),
        )

    if len(parts) == 4:
        return (
            _normalize_report_datetime(parts[0] + " " + parts[1]),
            _normalize_report_datetime(parts[2] + " " + parts[3], is_end=True),
        )

    raise ValueError("invalid jobs_report period")


@router.message(Command("jobs"))
async def dispatcher_jobs(message: Message) -> None:
    if message.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    async with async_session_maker() as session:
        repository = JobRepository(session)
        jobs = await repository.list_recent_jobs(limit=20)

    await _send_jobs_list(
        message=message,
        title="<b>Последние заявки CargoPT</b>",
        empty_text="Заявок пока нет.",
        jobs=jobs,
    )


@router.message(Command("jobs_attention"))
async def dispatcher_jobs_attention(message: Message) -> None:
    if message.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    async with async_session_maker() as session:
        repository = JobRepository(session)
        jobs = await repository.list_attention_jobs(limit=20)

    await _send_jobs_list(
        message=message,
        title="<b>Заявки CargoPT, требующие внимания</b>",
        empty_text="Заявок, требующих внимания, нет.",
        jobs=jobs,
    )



def _parse_job_command_id(text: str | None) -> int | None:
    raw = (text or "").strip()
    if not raw:
        return None

    if raw.startswith("/job_"):
        value = raw.split()[0].removeprefix("/job_")
    else:
        parts = raw.split()
        if len(parts) < 2 or parts[0] != "/job":
            return None
        value = parts[1]

    if not value.isdigit():
        return None

    return int(value)


def _job_admin_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔁 Повторить рассылку",
                    callback_data=f"job:{job_id}:retry",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Отправить вручную",
                    callback_data=f"job:{job_id}:manual",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Закрыть вручную",
                    callback_data=f"job:{job_id}:close",
                ),
            ],
        ],
    )


@router.message(Command("job"))
@router.message(lambda message: bool((message.text or "").strip().startswith("/job_")))
async def dispatcher_job_detail(message: Message) -> None:
    if message.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    job_id = _parse_job_command_id(message.text)
    if job_id is None:
        await message.answer("Формат: /job 26 или /job_26")
        return

    async with async_session_maker() as session:
        repository = JobRepository(session)
        job = await repository.get_job_by_id(job_id)

        if job is None:
            await message.answer(f"Заявка #{_safe(job_id)} не найдена.", parse_mode="HTML")
            return

        addresses = await repository.list_addresses_by_job(job.id)
        items = await repository.list_items_by_job(job.id)
        offers = await repository.list_offers_by_job(job.id)

    await message.answer(
        _build_job_card_text(
            job=job,
            addresses=addresses,
            items=items,
            offers=offers,
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=_job_admin_keyboard(job.id),
    )


@router.callback_query(F.data.startswith("job:"))
async def dispatcher_job_admin_action(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer("Некорректное действие.", show_alert=True)
        return

    _, raw_job_id, action = parts
    if not raw_job_id.isdigit() or action not in {"retry", "manual", "close"}:
        await callback.answer("Некорректное действие.", show_alert=True)
        return

    if action == "retry":
        async with async_session_maker() as session:
            job_repository = JobRepository(session)
            carrier_repository = CarrierRepository(session)
            job = await job_repository.get_job_by_id(int(raw_job_id))

            if job is None:
                await callback.answer(
                    f"Заявка #{raw_job_id} не найдена.",
                    show_alert=True,
                )
                return

            previous_status = job.status
            distribution = OfferDistributionService(
                matching_service=JobMatchingService(
                    CarrierSearchService(carrier_repository)
                ),
                offer_service=JobOfferService(job_repository),
                job_repository=job_repository,
            )

            offers = await distribution.create_offers_for_job(
                job,
                limit=None,
                expires_in_minutes=60,
            )

            if not offers:
                await job_repository.update_job_status(
                    job_id=job.id,
                    status=previous_status,
                    updated_at=job.updated_at,
                )
                await session.commit()
                await callback.answer(
                    f"Заявка #{job.id}: новых перевозчиков для рассылки не найдено.",
                    show_alert=True,
                )
                return

            sent_count = await send_job_offers_to_carriers(
                bot=callback.bot,
                job=job,
                offers=offers,
                job_repository=job_repository,
                carrier_repository=carrier_repository,
            )
            await session.commit()

        await callback.answer(
            f"Заявка #{raw_job_id}: создано офферов — {len(offers)}, отправлено — {sent_count}.",
            show_alert=True,
        )
        if callback.message:
            await callback.message.answer(
                f"Повторная рассылка заявки #{raw_job_id} выполнена.\n"
                f"Создано офферов: {len(offers)}\n"
                f"Отправлено перевозчикам: {sent_count}"
            )
        return

    labels = {
        "manual": "Ручная отправка перевозчику",
        "close": "Ручное закрытие заявки",
    }
    await callback.answer(
        f"{labels[action]} для заявки #{raw_job_id}: функция в разработке.",
        show_alert=True,
    )


@router.message(Command("jobs_report"))
async def dispatcher_jobs_report(message: Message) -> None:
    if message.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    try:
        since_text, until_text = _parse_jobs_report_period(message.text or "")
    except ValueError:
        await message.answer(
            "Формат: /jobs_report [YYYY-MM-DD] [YYYY-MM-DD]\n"
            "Или: /jobs_report YYYY-MM-DD HH:MM YYYY-MM-DD HH:MM"
        )
        return

    period_filter = "created_at >= :since"
    params = {"since": since_text}

    if until_text is not None:
        period_filter += " AND created_at <= :until"
        params["until"] = until_text

    async with async_session_maker() as session:
        job_rows = (
            await session.execute(
                text(f"""
                    SELECT status, COUNT(*) AS count
                    FROM job
                    WHERE {period_filter}
                    GROUP BY status
                    ORDER BY count DESC, status
                """),
                params,
            )
        ).mappings().all()

        offer_rows = (
            await session.execute(
                text(f"""
                    SELECT o.status, COUNT(*) AS count
                    FROM job_offer o
                    JOIN job j ON j.id = o.job_id
                    WHERE {period_filter.replace("created_at", "j.created_at")}
                    GROUP BY o.status
                    ORDER BY count DESC, o.status
                """),
                params,
            )
        ).mappings().all()

        job_detail_rows = (
            await session.execute(
                text(f"""
                    SELECT
                        j.id,
                        j.status,
                        j.client_telegram_username,
                        j.client_telegram_user_id,
                        COUNT(o.id) AS offers,
                        COALESCE(SUM(CASE WHEN o.status = 'accepted' THEN 1 ELSE 0 END), 0) AS accepted,
                        COALESCE(SUM(CASE WHEN o.status = 'declined' THEN 1 ELSE 0 END), 0) AS declined,
                        COALESCE(SUM(CASE WHEN o.status = 'expired' THEN 1 ELSE 0 END), 0) AS expired,
                        COALESCE(SUM(CASE WHEN o.status = 'pending' THEN 1 ELSE 0 END), 0) AS pending,
                        MAX(o.decline_reason) AS latest_reason
                    FROM job j
                    LEFT JOIN job_offer o ON o.job_id = j.id
                    WHERE {period_filter.replace("created_at", "j.created_at")}
                    GROUP BY j.id
                    ORDER BY j.id
                """),
                params,
            )
        ).mappings().all()

    report = (
        "<b>CargoPT jobs report</b>\n"
        f"Период: с {_safe(since_text)} UTC"
        + (f" по {_safe(until_text)} UTC" if until_text else "")
        + "\n\n"
        "<b>Заявки</b>\n"
        f"{_format_status_counts(job_rows)}\n\n"
        "<b>Офферы</b>\n"
        f"{_format_offer_counts(offer_rows)}\n\n"
        "<b>По заявкам</b>\n"
        f"{_format_report_job_rows(job_detail_rows)}"
    )

    await message.answer(report, parse_mode="HTML")
