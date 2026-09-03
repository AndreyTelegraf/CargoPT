import html
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlencode

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup
from aiogram.types import Message
from sqlalchemy import text

from app.domain.admin_access import (
    CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS,
    CARGOPT_OPERATOR_TELEGRAM_USER_IDS,
)
from app.db.session import async_session_maker
from app.domain.job_decline_reason import get_decline_reason_label
from app.domain.requested_date import PORTUGAL_TIMEZONE
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService
from app.services.job_offer import JobOfferService
from app.services.offer_distribution import OfferDistributionService
from app.services.offer_notification import send_job_offers_to_carriers
from app.services.job_completion import send_completion_result_notifications

router = Router()


MANUAL_DISPATCH_PAGE_SIZE = 10


ACQUISITION_INTERNAL_TRAFFIC_SQL = """
(
    COALESCE(j.source, '') IN (
        'synthetic_test',
        'synthetic_fsm_track_test'
    )
    OR COALESCE(j.utm_source, '') IN (
        'internal_test',
        'synthetic',
        'synthetic_acceptance',
        'https_smoke',
        'manual_audit',
        'manual_visual_smoke'
    )
    OR COALESCE(j.utm_campaign, '') IN (
        'floor_elevator_smoke'
    )
    OR COALESCE(j.landing_version, '') IN (
        'synthetic',
        'synthetic-test-carriers-16-17',
        'synthetic-test-carrier-17',
        'manual_audit',
        'manual_visual_smoke',
        'runtime_audit',
        'contract_verify'
    )
)
"""


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_dt(value) -> str:
    if value is None:
        return "—"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return _safe(
        value.astimezone(PORTUGAL_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    )


STATUS_LABELS = {
    "draft": "черновик",
    "draft_expired": "архивный черновик",
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


def _format_acquisition_rate(value: int, submitted: int) -> str:
    if submitted <= 0:
        return "—"
    return f"{value / submitted:.1%}"


def _format_acquisition_snapshot(summary, rows) -> str:
    submitted = int(summary["submitted"] or 0)

    summary_lines = (
        f"Production records: {_safe(summary['records'] or 0)}",
        f"Excluded internal/test: {_safe(summary['excluded_internal'] or 0)}",
        f"Drafts: {_safe(summary['drafts'] or 0)}",
        f"Submitted: {_safe(submitted)}",
        (
            f"Has offers: {_safe(summary['has_offers'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['has_offers'] or 0, submitted))})"
        ),
        (
            f"Accepted now: {_safe(summary['accepted_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['accepted_now'] or 0, submitted))})"
        ),
        (
            f"Assignment signal: {_safe(summary['assignment_signal'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['assignment_signal'] or 0, submitted))})"
        ),
        (
            f"Assigned now: {_safe(summary['assigned_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['assigned_now'] or 0, submitted))})"
        ),
        (
            f"In progress now: {_safe(summary['in_progress_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['in_progress_now'] or 0, submitted))})"
        ),
        (
            f"Completed now: {_safe(summary['completed_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['completed_now'] or 0, submitted))})"
        ),
        (
            f"Cancelled now: {_safe(summary['cancelled_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['cancelled_now'] or 0, submitted))})"
        ),
    )

    group_lines = []
    for row in rows:
        group_lines.append(
            (
                f"<b>{_safe(row['source'])} / {_safe(row['utm_source'])} / "
                f"{_safe(row['utm_medium'])} / {_safe(row['utm_campaign'])}</b>\n"
                f"submitted={_safe(row['submitted'])} | "
                f"offers={_safe(row['has_offers'])} | "
                f"accepted_now={_safe(row['accepted_now'])} | "
                f"assignment_signal={_safe(row['assignment_signal'])} | "
                f"assigned_now={_safe(row['assigned_now'])} | "
                f"completed_now={_safe(row['completed_now'])}"
            )
        )

    groups = "\n\n".join(group_lines) if group_lines else "—"

    return (
        "<b>Snapshot</b>\n"
        + "\n".join(summary_lines)
        + "\n\n"
        + "<b>Acquisition groups — top 10</b>\n"
        + groups
    )


def _format_report_status(row) -> str:
    if row["status"] == "offered" and row["accepted"] > 0:
        return "ожидает выбора клиента"
    return _format_status(row["status"])


def _format_report_job_rows(rows) -> str:
    if not rows:
        return "—"

    lines = []
    for row in rows:
        client = row["client_telegram_username"] or str(row["client_telegram_user_id"])
        line = (
            f"<b>#{_safe(row['id'])}</b> — {_safe(_format_report_status(row))} — @{_safe(client)}\n"
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
    if getattr(address, "country_code", None):
        details.append(f"страна: {_safe(address.country_code.upper())}")
    if getattr(address, "address_details", None):
        details.append(f"квартира / доступ: {_safe(address.address_details)}")
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
        f"Авторассылка по сроку: "
        f"{'заблокирована — менее 72 ч' if job.short_lead_time_filtered else 'разрешена'}\n\n"
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
        f"UTM source: {_format_optional(job.utm_source)}\n"
        f"UTM medium: {_format_optional(job.utm_medium)}\n"
        f"UTM campaign: {_format_optional(job.utm_campaign)}\n"
        f"UTM content: {_format_optional(job.utm_content)}\n"
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
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
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
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
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


def _job_admin_keyboard(job) -> InlineKeyboardMarkup:
    rows = [
            [
                InlineKeyboardButton(
                    text="🔁 Повторить рассылку",
                    callback_data=f"job:{job.id}:retry",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚚 Отправить вручную",
                    callback_data=f"job:{job.id}:manual",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Закрыть вручную",
                    callback_data=f"job:{job.id}:close",
                ),
            ],
        ]
    if job.status in {"assigned", "in_progress"}:
        rows.insert(
            2,
            [
                InlineKeyboardButton(
                    text="Завершить заявку",
                    callback_data=f"job:{job.id}:complete",
                )
            ],
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _job_completion_confirmation_keyboard(job_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Подтвердить завершение",
                    callback_data=f"job:{job_id}:complete_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=f"job:{job_id}:complete_cancel",
                )
            ],
        ]
    )


async def _build_manual_dispatch_keyboard(
    *,
    job,
    job_repository: JobRepository,
    carrier_repository: CarrierRepository,
    page: int = 0,
    carrier_query: str | None = None,
) -> tuple[InlineKeyboardMarkup, int, int, int]:
    offers = await job_repository.list_offers_by_job(job.id)
    active_offer_statuses = {}
    for offer in offers:
        if offer.status == "accepted":
            active_offer_statuses[offer.carrier_id] = "accepted"
        elif offer.status == "pending" and offer.carrier_id not in active_offer_statuses:
            active_offer_statuses[offer.carrier_id] = "pending"

    addresses = await job_repository.list_addresses_by_job(job.id)
    matching_vehicles = await JobMatchingService(
        CarrierSearchService(carrier_repository)
    ).find_matching_vehicles_for_job(
        job,
        addresses=addresses,
    )

    carriers = await carrier_repository.list_all_carriers()
    normalized_query = (carrier_query or "").strip().lstrip("@").casefold()
    if normalized_query:
        carriers = [
            carrier
            for carrier in carriers
            if normalized_query in carrier.company_name.casefold().lstrip("@")
            or normalized_query
            in (carrier.telegram_username or "").casefold().lstrip("@")
        ]
    all_vehicles = await carrier_repository.list_all_vehicles()
    active_vehicles_by_carrier = {}
    for vehicle in all_vehicles:
        if vehicle.is_active:
            active_vehicles_by_carrier.setdefault(vehicle.carrier_id, []).append(vehicle)

    matching_vehicle_by_carrier = {}
    for vehicle in matching_vehicles:
        matching_vehicle_by_carrier.setdefault(vehicle.carrier_id, vehicle)

    now = datetime.now(UTC)
    entries = []
    status_labels = {
        "draft": "черновик",
        "invited": "invited",
        "pending_moderation": "на модерации",
        "suspended": "приостановлен",
        "rejected": "отклонён",
        "profile_completed": "профиль не активирован",
    }

    for carrier in carriers:
        matching_vehicle = matching_vehicle_by_carrier.get(carrier.id)
        active_vehicles = active_vehicles_by_carrier.get(carrier.id, [])
        vehicle = matching_vehicle or (active_vehicles[0] if active_vehicles else None)
        active_offer_status = active_offer_statuses.get(carrier.id)
        paid_until = carrier.paid_until
        if paid_until is not None and paid_until.tzinfo is None:
            paid_until = paid_until.replace(tzinfo=UTC)

        group = 3
        sendable = False
        prefix = ""

        if active_offer_status == "accepted":
            group = 2
            prefix = "[оффер принят] "
        elif active_offer_status == "pending":
            group = 2
            prefix = "[оффер ожидает] "
        elif carrier.status != "active":
            prefix = f"[{status_labels.get(carrier.status, carrier.status)}] "
        elif paid_until is None:
            prefix = "[нет подписки] "
        elif paid_until < now:
            prefix = "[подписка истекла] "
        elif carrier.telegram_user_id is None:
            prefix = "[нет Telegram] "
        elif vehicle is None:
            prefix = "[нет машины] "
        else:
            sendable = True
            if matching_vehicle is not None:
                group = 0
            else:
                group = 1
                prefix = "[вне фильтра] "

        vehicle_label = f" · {vehicle.vehicle_type}" if vehicle is not None else ""
        label = f"{prefix}{carrier.company_name}{vehicle_label}"
        callback_data = (
            f"job:{job.id}:send:{vehicle.id}"
            if sendable and vehicle is not None
            else f"job:{job.id}:noop"
        )
        entries.append((group, carrier.company_name.casefold(), label, callback_data))

    entries.sort(key=lambda item: (item[0], item[1]))
    total_entries = len(entries)
    page_size = (total_entries or 1) if normalized_query else MANUAL_DISPATCH_PAGE_SIZE
    total_pages = max(1, (total_entries + page_size - 1) // page_size)
    safe_page = min(max(page, 0), total_pages - 1)
    start = safe_page * page_size
    page_entries = entries[start : start + page_size]

    rows = [
        [
            InlineKeyboardButton(
                text=label[:64],
                callback_data=callback_data,
            )
        ]
        for _, _, label, callback_data in page_entries
    ]

    navigation = []
    if safe_page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"job:{job.id}:manual:{safe_page - 1}",
            )
        )
    navigation.append(
        InlineKeyboardButton(
            text=f"{safe_page + 1}/{total_pages}",
            callback_data=f"job:{job.id}:noop",
        )
    )
    if safe_page + 1 < total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"job:{job.id}:manual:{safe_page + 1}",
            )
        )
    rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="↩️ Назад к заявке",
                callback_data=f"job:{job.id}:back",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows), safe_page, total_pages, total_entries


def _manual_dispatch_page_text(
    *,
    job_id: int,
    page: int,
    total_pages: int,
    total_entries: int,
    carrier_query: str | None = None,
) -> str:
    search_line = (
        f"Поиск: {carrier_query}\n" if (carrier_query or "").strip() else ""
    )
    return (
        f"Перевозчики для ручной отправки заявки #{job_id}\n"
        f"Страница {page + 1}/{total_pages} · всего {total_entries}\n\n"
        f"{search_line}"
        "[вне фильтра] — можно отправить вручную; "
        "остальные статусы — информационные.\n\n"
        f"Поиск: /job_carriers {job_id} @username или название"
    )


@router.message(Command("job"))
@router.message(lambda message: bool((message.text or "").strip().startswith("/job_")))
async def dispatcher_job_detail(message: Message) -> None:
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
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
        reply_markup=_job_admin_keyboard(job),
    )


@router.message(Command("job_carriers"))
async def dispatcher_job_carrier_search(message: Message) -> None:
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    parts = (message.text or "").strip().split(maxsplit=2)
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].strip():
        await message.answer(
            "Формат: /job_carriers 138 @username или название перевозчика"
        )
        return

    job_id = int(parts[1])
    carrier_query = parts[2].strip()
    async with async_session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        job = await job_repository.get_job_by_id(job_id)
        if job is None:
            await message.answer(f"Заявка #{job_id} не найдена.")
            return
        keyboard, page, total_pages, total_entries = (
            await _build_manual_dispatch_keyboard(
                job=job,
                job_repository=job_repository,
                carrier_repository=carrier_repository,
                carrier_query=carrier_query,
            )
        )

    if total_entries == 0:
        await message.answer(
            f"По запросу «{_safe(carrier_query)}» перевозчики не найдены.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        _manual_dispatch_page_text(
            job_id=job_id,
            page=page,
            total_pages=total_pages,
            total_entries=total_entries,
            carrier_query=carrier_query,
        ),
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("job:"))
async def dispatcher_job_admin_action(callback: CallbackQuery) -> None:
    if callback.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
        await callback.answer("Недостаточно прав.", show_alert=True)
        return

    parts = (callback.data or "").split(":")
    if len(parts) not in {3, 4}:
        await callback.answer("Некорректное действие.", show_alert=True)
        return

    _, raw_job_id, action, *extra = parts
    if not raw_job_id.isdigit() or action not in {
        "retry",
        "manual",
        "close",
        "back",
        "send",
        "noop",
        "complete",
        "complete_confirm",
        "complete_cancel",
    }:
        await callback.answer("Некорректное действие.", show_alert=True)
        return

    if action == "noop":
        await callback.answer(
            "Информационная строка: отправка этому перевозчику сейчас недоступна.",
            show_alert=True,
        )
        return

    if action in {"complete", "complete_cancel"}:
        async with async_session_maker() as session:
            job = await JobRepository(session).get_job_by_id(int(raw_job_id))
        if job is None:
            await callback.answer("Заявка не найдена.", show_alert=True)
            return
        if job.status not in {"assigned", "in_progress"}:
            await callback.answer(
                f"Заявку в статусе {job.status} нельзя завершить вручную.",
                show_alert=True,
            )
            return
        if callback.message:
            keyboard = (
                _job_completion_confirmation_keyboard(job.id)
                if action == "complete"
                else _job_admin_keyboard(job)
            )
            await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer(
            "Подтвердите завершение." if action == "complete" else "Действие отменено."
        )
        return

    if action == "complete_confirm":
        async with async_session_maker() as session:
            job_repository = JobRepository(session)
            carrier_repository = CarrierRepository(session)
            job = await job_repository.get_job_by_id(int(raw_job_id))
            if job is None:
                await callback.answer("Заявка не найдена.", show_alert=True)
                return
            if job.status not in {"assigned", "in_progress"}:
                await callback.answer(
                    f"Заявку в статусе {job.status} нельзя завершить вручную.",
                    show_alert=True,
                )
                return
            job = await job_repository.update_job_status(
                job_id=job.id,
                status="completed",
                updated_at=datetime.now(UTC),
            )
            accepted_offer = await job_repository.get_accepted_offer_by_job_id(job.id)
            await session.commit()
            await send_completion_result_notifications(
                bot=callback.bot,
                job=job,
                accepted_offer=accepted_offer,
                carrier_repository=carrier_repository,
                completed_by_dispatcher=True,
            )
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer(
                f"Заявка #{job.id} вручную переведена в статус completed."
            )
        await callback.answer("Заявка завершена.", show_alert=True)
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

    if action == "close":
        carrier_message_refs: list[tuple[int | None, int | None]] = []

        async with async_session_maker() as session:
            job_repository = JobRepository(session)
            job = await job_repository.get_job_by_id(int(raw_job_id))

            if job is None:
                await callback.answer(
                    f"Заявка #{raw_job_id} не найдена.",
                    show_alert=True,
                )
                return

            offers = await job_repository.list_offers_by_job(job.id)
            carrier_message_refs = [
                (offer.carrier_message_chat_id, offer.carrier_message_id)
                for offer in offers
                if offer.status in {"pending", "accepted"}
                and offer.carrier_message_chat_id is not None
                and offer.carrier_message_id is not None
            ]

            now = datetime.now(UTC)

            for offer in offers:
                if offer.status == "pending":
                    await job_repository.update_offer_status(
                        offer.id,
                        status="declined",
                        responded_at=now,
                        decline_reason="admin_closed",
                    )
                elif offer.status == "accepted":
                    await job_repository.update_offer_status(
                        offer.id,
                        status="cancelled",
                        responded_at=now,
                    )

            await job_repository.clear_assignment_confirmation_statuses(
                job_id=job.id,
                updated_at=now,
            )
            await job_repository.update_job_status(
                job_id=job.id,
                status="cancelled",
                updated_at=now,
            )
            await session.commit()

        for chat_id, message_id in carrier_message_refs:
            try:
                await callback.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass

        await callback.answer(
            f"Заявка #{raw_job_id} закрыта.",
            show_alert=True,
        )

        if callback.message:
            await callback.message.answer(
                f"Заявка #{raw_job_id} вручную переведена в статус cancelled, активные офферы закрыты, карточки у перевозчиков удалены."
            )
        return

    if action == "manual":
        if len(extra) > 1 or (extra and not extra[0].isdigit()):
            await callback.answer("Некорректная страница.", show_alert=True)
            return
        requested_page = int(extra[0]) if extra else 0

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

            keyboard, page, total_pages, total_entries = await _build_manual_dispatch_keyboard(
                job=job,
                job_repository=job_repository,
                carrier_repository=carrier_repository,
                page=requested_page,
            )

        if total_entries == 0:
            await callback.answer(
                f"Заявка #{raw_job_id}: реестр перевозчиков пуст.",
                show_alert=True,
            )
            return

        if callback.message:
            page_text = _manual_dispatch_page_text(
                job_id=int(raw_job_id),
                page=page,
                total_pages=total_pages,
                total_entries=total_entries,
            )
            if extra:
                await callback.message.edit_text(page_text, reply_markup=keyboard)
            else:
                await callback.message.answer(page_text, reply_markup=keyboard)

        await callback.answer("Список перевозчиков сформирован.")
        return

    if action == "send":
        if len(extra) != 1 or not extra[0].isdigit():
            await callback.answer("Некорректное действие.", show_alert=True)
            return

        vehicle_id = int(extra[0])

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

            vehicle = await carrier_repository.get_vehicle_by_id(vehicle_id)
            if vehicle is None:
                await callback.answer(
                    "Автомобиль перевозчика не найден.",
                    show_alert=True,
                )
                return

            carrier = await carrier_repository.get_carrier_by_vehicle_id(vehicle.id)
            if carrier is None or carrier.telegram_user_id is None:
                await callback.answer(
                    "У перевозчика нет Telegram ID для отправки.",
                    show_alert=True,
                )
                return

            now = datetime.now(UTC)
            paid_until = carrier.paid_until
            if paid_until is not None and paid_until.tzinfo is None:
                paid_until = paid_until.replace(tzinfo=UTC)
            if carrier.status != "active":
                await callback.answer(
                    "Перевозчик сейчас не активен.",
                    show_alert=True,
                )
                return
            if paid_until is None or paid_until < now:
                await callback.answer(
                    "У перевозчика нет действующей подписки.",
                    show_alert=True,
                )
                return
            if not vehicle.is_active:
                await callback.answer(
                    "Автомобиль перевозчика не активен.",
                    show_alert=True,
                )
                return

            active_offer_carrier_ids = (
                await job_repository.list_active_offer_carrier_ids_by_job(job.id)
            )
            if vehicle.carrier_id in active_offer_carrier_ids:
                await callback.answer(
                    f"Заявка #{job.id}: у перевозчика уже есть активный оффер.",
                    show_alert=True,
                )
                return

            offer = await JobOfferService(job_repository).create_offer(
                job_id=job.id,
                vehicle=vehicle,
                expires_in_minutes=60,
            )

            await job_repository.update_job_status(
                job_id=job.id,
                status="offered",
                updated_at=job.updated_at,
            )

            sent_count = await send_job_offers_to_carriers(
                bot=callback.bot,
                job=job,
                offers=[offer],
                job_repository=job_repository,
                carrier_repository=carrier_repository,
            )
            await session.commit()

        if sent_count == 0:
            await callback.answer(
                f"Оффер создан, но отправка перевозчику #{vehicle.carrier_id} не подтвердилась.",
                show_alert=True,
            )
            return

        await callback.answer(
            f"Заявка #{raw_job_id} отправлена перевозчику {carrier.company_name}.",
            show_alert=True,
        )

        if callback.message:
            await callback.message.answer(
                f"Заявка #{raw_job_id} вручную отправлена перевозчику:\n"
                f"{carrier.company_name}\n"
                f"Оффер #{offer.id}"
            )
        return

    if action == "back":
        await callback.answer("Откройте карточку заявки командой /job " + raw_job_id)
        return

    await callback.answer("Некорректное действие.", show_alert=True)


@router.message(Command("jobs_acquisition"))
async def dispatcher_jobs_acquisition(message: Message) -> None:
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только диспетчеру CargoPT.")
        return

    try:
        since_text, until_text = _parse_jobs_report_period(message.text or "")
    except ValueError:
        await message.answer(
            "Формат: /jobs_acquisition [YYYY-MM-DD] [YYYY-MM-DD]\n"
            "Или: /jobs_acquisition "
            "YYYY-MM-DD HH:MM YYYY-MM-DD HH:MM"
        )
        return

    period_filter = "j.created_at >= :since"
    params = {"since": since_text}

    if until_text is not None:
        period_filter += " AND j.created_at <= :until"
        params["until"] = until_text

    production_filter = (
        f"{period_filter} "
        f"AND NOT {ACQUISITION_INTERNAL_TRAFFIC_SQL}"
    )

    async with async_session_maker() as session:
        excluded_internal = (
            await session.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM job j
                    WHERE {period_filter}
                      AND {ACQUISITION_INTERNAL_TRAFFIC_SQL}
                """),
                params,
            )
        ).scalar_one()

        summary = (
            await session.execute(
                text(f"""
                    SELECT
                        COUNT(*) AS records,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'draft' THEN 1 ELSE 0
                        END), 0) AS drafts,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft' THEN 1 ELSE 0
                        END), 0) AS submitted,
                        COALESCE(SUM(CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM job_offer offer_exists
                                WHERE offer_exists.job_id = j.id
                            )
                            THEN 1 ELSE 0
                        END), 0) AS has_offers,
                        COALESCE(SUM(CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM job_offer accepted_offer
                                WHERE accepted_offer.job_id = j.id
                                  AND accepted_offer.status = 'accepted'
                            )
                            THEN 1 ELSE 0
                        END), 0) AS accepted_now,
                        COALESCE(SUM(CASE
                            WHEN j.assigned_at IS NOT NULL THEN 1 ELSE 0
                        END), 0) AS assignment_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'assigned' THEN 1 ELSE 0
                        END), 0) AS assigned_now,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'in_progress' THEN 1 ELSE 0
                        END), 0) AS in_progress_now,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'completed' THEN 1 ELSE 0
                        END), 0) AS completed_now,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'cancelled' THEN 1 ELSE 0
                        END), 0) AS cancelled_now
                    FROM job j
                    WHERE {production_filter}
                """),
                params,
            )
        ).mappings().one()

        summary = dict(summary)
        summary["excluded_internal"] = excluded_internal

        acquisition_rows = (
            await session.execute(
                text(f"""
                    SELECT
                        COALESCE(NULLIF(j.source, ''), '—') AS source,
                        COALESCE(NULLIF(j.utm_source, ''), '—')
                            AS utm_source,
                        COALESCE(NULLIF(j.utm_medium, ''), '—')
                            AS utm_medium,
                        COALESCE(NULLIF(j.utm_campaign, ''), '—')
                            AS utm_campaign,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft' THEN 1 ELSE 0
                        END), 0) AS submitted,
                        COALESCE(SUM(CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM job_offer offer_exists
                                WHERE offer_exists.job_id = j.id
                            )
                            THEN 1 ELSE 0
                        END), 0) AS has_offers,
                        COALESCE(SUM(CASE
                            WHEN EXISTS (
                                SELECT 1
                                FROM job_offer accepted_offer
                                WHERE accepted_offer.job_id = j.id
                                  AND accepted_offer.status = 'accepted'
                            )
                            THEN 1 ELSE 0
                        END), 0) AS accepted_now,
                        COALESCE(SUM(CASE
                            WHEN j.assigned_at IS NOT NULL THEN 1 ELSE 0
                        END), 0) AS assignment_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'assigned' THEN 1 ELSE 0
                        END), 0) AS assigned_now,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'completed' THEN 1 ELSE 0
                        END), 0) AS completed_now
                    FROM job j
                    WHERE {production_filter}
                    GROUP BY 1, 2, 3, 4
                    HAVING submitted > 0
                    ORDER BY
                        submitted DESC,
                        has_offers DESC,
                        source,
                        utm_source,
                        utm_campaign
                    LIMIT 10
                """),
                params,
            )
        ).mappings().all()

    report = (
        "<b>CargoPT acquisition snapshot</b>\n"
        f"Период: с {_safe(since_text)} UTC"
        + (f" по {_safe(until_text)} UTC" if until_text else "")
        + "\n\n"
        + _format_acquisition_snapshot(summary, acquisition_rows)
        + "\n\n"
        + "<i>internal/test исключены по явному реестру маркеров. "
        "assignment_signal = assigned_at заполнен; "
        "это не обязательно текущая назначенная сделка.</i>"
    )

    if len(report) > 4096:
        await message.answer(
            "Acquisition snapshot превышает лимит Telegram. "
            "Укажите более короткий период."
        )
        return

    await message.answer(report, parse_mode="HTML")


@router.message(Command("jobs_report"))
async def dispatcher_jobs_report(message: Message) -> None:
    if message.from_user.id not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS:
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

    report_header = (
        "<b>CargoPT jobs report</b>\n"
        f"Период: с {_safe(since_text)} UTC"
        + (f" по {_safe(until_text)} UTC" if until_text else "")
        + "\n\n"
        "<b>Заявки</b>\n"
        f"{_format_status_counts(job_rows)}\n\n"
        "<b>Офферы</b>\n"
        f"{_format_offer_counts(offer_rows)}\n\n"
        "<b>По заявкам</b>\n"
    )

    job_blocks = [
        _format_report_job_rows([row])
        for row in job_detail_rows
    ] or ["—"]

    message_parts = []
    current_part = report_header

    for job_block in job_blocks:
        separator = "" if current_part.endswith("\n") else "\n\n"
        candidate = current_part + separator + job_block

        if len(candidate) <= 4096:
            current_part = candidate
            continue

        message_parts.append(current_part)
        current_part = job_block

    if current_part:
        message_parts.append(current_part)

    for message_part in message_parts:
        await message.answer(message_part, parse_mode="HTML")

LEADS_PUBLIC_BASE_URL = "https://cargopt.pt"

LEADS_PERIOD_HELP = (
    "Период: 7d, 30d или две даты YYYY-MM-DD.\n"
    "Пример: /leads 30d\n"
    "Пример: /leads 2026-07-01 2026-07-31"
)


def _parse_leads_date(value: str) -> datetime:
    try:
        return datetime.strptime(
            value,
            "%Y-%m-%d",
        ).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(
            "invalid leads report date"
        ) from exc


def _format_leads_sql_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def _parse_leads_period_args(
    args: list[str],
    *,
    now: datetime | None = None,
) -> tuple[str, str, str]:
    current = now or datetime.now(UTC)

    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)

    if not args:
        days = 7
        since = current - timedelta(days=days)
        return (
            f"последние {days} дней",
            _format_leads_sql_datetime(since),
            _format_leads_sql_datetime(current),
        )

    if len(args) == 1:
        token = args[0].strip().lower()

        if token.endswith("d") and token[:-1].isdigit():
            days = int(token[:-1])

            if days < 1 or days > 365:
                raise ValueError(
                    "leads report window must be "
                    "between 1 and 365 days"
                )

            since = current - timedelta(days=days)

            return (
                f"последние {days} дней",
                _format_leads_sql_datetime(since),
                _format_leads_sql_datetime(current),
            )

        since = _parse_leads_date(token)

        if since > current:
            raise ValueError(
                "leads report start is in the future"
            )

        return (
            f"с {token} по текущий момент",
            _format_leads_sql_datetime(since),
            _format_leads_sql_datetime(current),
        )

    if len(args) == 2:
        since = _parse_leads_date(args[0])
        until_date = _parse_leads_date(args[1])

        if since > until_date:
            raise ValueError(
                "leads report start is after end"
            )

        until = until_date.replace(
            hour=23,
            minute=59,
            second=59,
        )

        return (
            f"с {args[0]} по {args[1]}",
            _format_leads_sql_datetime(since),
            _format_leads_sql_datetime(until),
        )

    raise ValueError("invalid leads report period")


def _parse_leads_period(
    text_value: str,
    *,
    now: datetime | None = None,
) -> tuple[str, str, str]:
    return _parse_leads_period_args(
        text_value.split()[1:],
        now=now,
    )


def _format_leads_summary(summary) -> str:
    submitted = int(summary["submitted"] or 0)

    lines = (
        f"Веб-записи: {_safe(summary['records'] or 0)}",
        f"Черновики: {_safe(summary['drafts'] or 0)}",
        f"Отправленные заявки: {_safe(submitted)}",
        (
            f"Получили офферы: "
            f"{_safe(summary['has_offers'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['has_offers'] or 0, submitted))})"
        ),
        (
            f"Есть accepted-оффер сейчас: "
            f"{_safe(summary['accepted_now'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['accepted_now'] or 0, submitted))})"
        ),
        (
            f"Было назначение: "
            f"{_safe(summary['assignment_signal'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['assignment_signal'] or 0, submitted))})"
        ),
        (
            f"Завершены: "
            f"{_safe(summary['completed_signal'] or 0)} "
            f"({_safe(_format_acquisition_rate(summary['completed_signal'] or 0, submitted))})"
        ),
        f"Отменены сейчас: {_safe(summary['cancelled_now'] or 0)}",
    )

    return "\n".join(lines)


def _format_leads_group(row) -> str:
    return (
        f"<b>{_safe(row['source_locale'])} · "
        f"{_safe(row['utm_source'])} / "
        f"{_safe(row['utm_medium'])} / "
        f"{_safe(row['utm_campaign'])}</b>\n"
        f"submitted={_safe(row['submitted'])} | "
        f"offers={_safe(row['has_offers'])} | "
        f"accepted={_safe(row['accepted_now'])} | "
        f"assigned={_safe(row['assignment_signal'])} | "
        f"completed={_safe(row['completed_signal'])}"
    )


def _format_campaign_job(row) -> str:
    content = row["utm_content"] or "—"

    return (
        f"<b>/job_{_safe(row['id'])}</b> — "
        f"{_safe(_format_status(row['status']))}\n"
        f"{_safe(row['created_at'])} UTC · "
        f"{_safe(row['source_locale'] or '—')} · "
        f"content={_safe(content)}\n"
        f"offers={_safe(row['offers'])} | "
        f"accepted={_safe(row['accepted'])} | "
        f"assigned={'да' if row['assigned_at'] else 'нет'} | "
        f"completed={'да' if row['completed_at'] else 'нет'}"
    )


def _format_missing_job(row) -> str:
    missing = []

    if not row["utm_source"]:
        missing.append("source")
    if not row["utm_medium"]:
        missing.append("medium")
    if not row["utm_campaign"]:
        missing.append("campaign")
    if not row["utm_content"]:
        missing.append("content")

    return (
        f"<b>/job_{_safe(row['id'])}</b> — "
        f"{_safe(_format_status(row['status']))}\n"
        f"{_safe(row['created_at'])} UTC · "
        f"{_safe(row['source_locale'] or '—')} · "
        f"нет: {_safe(', '.join(missing))}"
    )


async def _send_html_blocks(
    *,
    message: Message,
    header: str,
    blocks: list[str],
) -> None:
    current = header

    for block in blocks:
        separator = (
            ""
            if not current
            else "\n\n"
        )
        candidate = current + separator + block

        if len(candidate) <= 4096:
            current = candidate
            continue

        if current:
            await message.answer(
                current,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )

        current = block

    if current:
        await message.answer(
            current,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


def _build_utm_link(
    *,
    locale: str,
    source: str,
    medium: str,
    campaign: str,
    content: str | None = None,
) -> str:
    normalized_locale = locale.strip().lower()

    locale_paths = {
        "pt": "/",
        "pt-pt": "/",
        "en": "/en/",
        "ru": "/ru/",
    }

    if normalized_locale not in locale_paths:
        raise ValueError(
            "locale must be pt, en or ru"
        )

    required_values = {
        "utm_source": source.strip(),
        "utm_medium": medium.strip(),
        "utm_campaign": campaign.strip(),
    }

    if not all(required_values.values()):
        raise ValueError(
            "source, medium and campaign are required"
        )

    for value in required_values.values():
        if len(value) > 255:
            raise ValueError(
                "UTM value is too long"
            )

    normalized_content = (
        content.strip()
        if content is not None
        else ""
    )

    if len(normalized_content) > 255:
        raise ValueError(
            "UTM content is too long"
        )

    params = dict(required_values)

    if normalized_content:
        params["utm_content"] = normalized_content

    return (
        LEADS_PUBLIC_BASE_URL
        + locale_paths[normalized_locale]
        + "?"
        + urlencode(params)
    )


@router.message(Command("leads"))
async def dispatcher_leads(message: Message) -> None:
    if message.from_user.id not in CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS:
        await message.answer(
            "Команда доступна только диспетчеру CargoPT."
        )
        return

    try:
        period_label, since_text, until_text = (
            _parse_leads_period(message.text or "")
        )
    except ValueError:
        await message.answer(LEADS_PERIOD_HELP)
        return

    params = {
        "since": since_text,
        "until": until_text,
    }

    production_filter = (
        "j.source = 'web_form' "
        "AND j.created_at >= :since "
        "AND j.created_at <= :until "
        f"AND NOT {ACQUISITION_INTERNAL_TRAFFIC_SQL}"
    )

    async with async_session_maker() as session:
        summary = (
            await session.execute(
                text(f"""
                    SELECT
                        COUNT(*) AS records,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS drafts,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS submitted,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer offer_exists
                                WHERE offer_exists.job_id = j.id
                             )
                            THEN 1 ELSE 0
                        END), 0) AS has_offers,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer accepted_offer
                                WHERE accepted_offer.job_id = j.id
                                  AND accepted_offer.status = 'accepted'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS accepted_now,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND j.assigned_at IS NOT NULL
                            THEN 1 ELSE 0
                        END), 0) AS assignment_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND (
                                j.completed_at IS NOT NULL
                                OR j.status = 'completed'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS completed_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'cancelled'
                            THEN 1 ELSE 0
                        END), 0) AS cancelled_now
                    FROM job j
                    WHERE {production_filter}
                """),
                params,
            )
        ).mappings().one()

        groups = (
            await session.execute(
                text(f"""
                    SELECT
                        COALESCE(
                            NULLIF(j.source_locale, ''),
                            '—'
                        ) AS source_locale,
                        COALESCE(
                            NULLIF(j.utm_source, ''),
                            '—'
                        ) AS utm_source,
                        COALESCE(
                            NULLIF(j.utm_medium, ''),
                            '—'
                        ) AS utm_medium,
                        COALESCE(
                            NULLIF(j.utm_campaign, ''),
                            '—'
                        ) AS utm_campaign,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS submitted,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer offer_exists
                                WHERE offer_exists.job_id = j.id
                             )
                            THEN 1 ELSE 0
                        END), 0) AS has_offers,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer accepted_offer
                                WHERE accepted_offer.job_id = j.id
                                  AND accepted_offer.status = 'accepted'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS accepted_now,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND j.assigned_at IS NOT NULL
                            THEN 1 ELSE 0
                        END), 0) AS assignment_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND (
                                j.completed_at IS NOT NULL
                                OR j.status = 'completed'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS completed_signal
                    FROM job j
                    WHERE {production_filter}
                    GROUP BY 1, 2, 3, 4
                    HAVING submitted > 0
                    ORDER BY
                        submitted DESC,
                        has_offers DESC,
                        source_locale,
                        utm_source,
                        utm_campaign
                    LIMIT 20
                """),
                params,
            )
        ).mappings().all()

    header = (
        "<b>CargoPT — лиды</b>\n"
        f"Период: {_safe(period_label)}\n"
        f"{_safe(since_text)} — "
        f"{_safe(until_text)} UTC\n\n"
        + _format_leads_summary(summary)
        + "\n\n<b>Источники</b>"
    )

    blocks = [
        _format_leads_group(row)
        for row in groups
    ] or ["—"]

    await _send_html_blocks(
        message=message,
        header=header,
        blocks=blocks,
    )


@router.message(Command("leads_campaign"))
async def dispatcher_leads_campaign(
    message: Message,
) -> None:
    if message.from_user.id not in CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS:
        await message.answer(
            "Команда доступна только диспетчеру CargoPT."
        )
        return

    parts = (message.text or "").split()

    if len(parts) < 2:
        await message.answer(
            "Формат: /leads_campaign "
            "<utm_campaign> [7d|30d|дата дата]"
        )
        return

    campaign = parts[1].strip()

    if not campaign or len(campaign) > 255:
        await message.answer(
            "Некорректное имя UTM campaign."
        )
        return

    try:
        period_label, since_text, until_text = (
            _parse_leads_period_args(parts[2:])
        )
    except ValueError:
        await message.answer(
            "Формат: /leads_campaign "
            "<utm_campaign> [7d|30d|дата дата]"
        )
        return

    params = {
        "campaign": campaign,
        "since": since_text,
        "until": until_text,
    }

    production_filter = (
        "j.source = 'web_form' "
        "AND j.utm_campaign = :campaign "
        "AND j.created_at >= :since "
        "AND j.created_at <= :until "
        f"AND NOT {ACQUISITION_INTERNAL_TRAFFIC_SQL}"
    )

    async with async_session_maker() as session:
        summary = (
            await session.execute(
                text(f"""
                    SELECT
                        COUNT(*) AS records,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS drafts,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS submitted,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer offer_exists
                                WHERE offer_exists.job_id = j.id
                             )
                            THEN 1 ELSE 0
                        END), 0) AS has_offers,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND EXISTS (
                                SELECT 1
                                FROM job_offer accepted_offer
                                WHERE accepted_offer.job_id = j.id
                                  AND accepted_offer.status = 'accepted'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS accepted_now,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND j.assigned_at IS NOT NULL
                            THEN 1 ELSE 0
                        END), 0) AS assignment_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                             AND (
                                j.completed_at IS NOT NULL
                                OR j.status = 'completed'
                             )
                            THEN 1 ELSE 0
                        END), 0) AS completed_signal,
                        COALESCE(SUM(CASE
                            WHEN j.status = 'cancelled'
                            THEN 1 ELSE 0
                        END), 0) AS cancelled_now
                    FROM job j
                    WHERE {production_filter}
                """),
                params,
            )
        ).mappings().one()

        content_rows = (
            await session.execute(
                text(f"""
                    SELECT
                        COALESCE(
                            NULLIF(j.source_locale, ''),
                            '—'
                        ) AS source_locale,
                        COALESCE(
                            NULLIF(j.utm_content, ''),
                            '—'
                        ) AS utm_content,
                        COUNT(*) AS records,
                        COALESCE(SUM(CASE
                            WHEN j.status <> 'draft'
                            THEN 1 ELSE 0
                        END), 0) AS submitted
                    FROM job j
                    WHERE {production_filter}
                    GROUP BY 1, 2
                    ORDER BY
                        submitted DESC,
                        records DESC,
                        source_locale,
                        utm_content
                    LIMIT 20
                """),
                params,
            )
        ).mappings().all()

        job_rows = (
            await session.execute(
                text(f"""
                    SELECT
                        j.id,
                        j.status,
                        j.created_at,
                        j.source_locale,
                        j.utm_content,
                        j.assigned_at,
                        j.completed_at,
                        COUNT(o.id) AS offers,
                        COALESCE(SUM(CASE
                            WHEN o.status = 'accepted'
                            THEN 1 ELSE 0
                        END), 0) AS accepted
                    FROM job j
                    LEFT JOIN job_offer o
                      ON o.job_id = j.id
                    WHERE {production_filter}
                    GROUP BY j.id
                    ORDER BY j.created_at DESC
                    LIMIT 50
                """),
                params,
            )
        ).mappings().all()

    content_text = "\n".join(
        (
            f"{_safe(row['source_locale'])} · "
            f"{_safe(row['utm_content'])}: "
            f"records={_safe(row['records'])}, "
            f"submitted={_safe(row['submitted'])}"
        )
        for row in content_rows
    ) or "—"

    header = (
        "<b>CargoPT — кампания</b>\n"
        f"Campaign: <code>{_safe(campaign)}</code>\n"
        f"Период: {_safe(period_label)}\n\n"
        + _format_leads_summary(summary)
        + "\n\n<b>Locale / content</b>\n"
        + content_text
        + "\n\n<b>Заявки</b>"
    )

    blocks = [
        _format_campaign_job(row)
        for row in job_rows
    ] or ["—"]

    await _send_html_blocks(
        message=message,
        header=header,
        blocks=blocks,
    )


@router.message(Command("leads_missing"))
async def dispatcher_leads_missing(
    message: Message,
) -> None:
    if message.from_user.id not in CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS:
        await message.answer(
            "Команда доступна только диспетчеру CargoPT."
        )
        return

    try:
        period_label, since_text, until_text = (
            _parse_leads_period(message.text or "")
        )
    except ValueError:
        await message.answer(LEADS_PERIOD_HELP)
        return

    params = {
        "since": since_text,
        "until": until_text,
    }

    production_filter = (
        "j.source = 'web_form' "
        "AND j.created_at >= :since "
        "AND j.created_at <= :until "
        f"AND NOT {ACQUISITION_INTERNAL_TRAFFIC_SQL}"
    )

    missing_filter = """
    (
        COALESCE(j.utm_source, '') = ''
        OR COALESCE(j.utm_medium, '') = ''
        OR COALESCE(j.utm_campaign, '') = ''
        OR COALESCE(j.utm_content, '') = ''
    )
    """

    async with async_session_maker() as session:
        summary = (
            await session.execute(
                text(f"""
                    SELECT
                        COUNT(*) AS records,
                        COALESCE(SUM(CASE
                            WHEN COALESCE(j.utm_source, '') = ''
                            THEN 1 ELSE 0
                        END), 0) AS missing_source,
                        COALESCE(SUM(CASE
                            WHEN COALESCE(j.utm_medium, '') = ''
                            THEN 1 ELSE 0
                        END), 0) AS missing_medium,
                        COALESCE(SUM(CASE
                            WHEN COALESCE(j.utm_campaign, '') = ''
                            THEN 1 ELSE 0
                        END), 0) AS missing_campaign,
                        COALESCE(SUM(CASE
                            WHEN COALESCE(j.utm_content, '') = ''
                            THEN 1 ELSE 0
                        END), 0) AS missing_content
                    FROM job j
                    WHERE {production_filter}
                      AND {missing_filter}
                """),
                params,
            )
        ).mappings().one()

        job_rows = (
            await session.execute(
                text(f"""
                    SELECT
                        j.id,
                        j.status,
                        j.created_at,
                        j.source_locale,
                        j.utm_source,
                        j.utm_medium,
                        j.utm_campaign,
                        j.utm_content
                    FROM job j
                    WHERE {production_filter}
                      AND {missing_filter}
                    ORDER BY j.created_at DESC
                    LIMIT 50
                """),
                params,
            )
        ).mappings().all()

    header = (
        "<b>CargoPT — неполная атрибуция</b>\n"
        f"Период: {_safe(period_label)}\n\n"
        f"Заявок с пропусками: "
        f"{_safe(summary['records'] or 0)}\n"
        f"Без source: "
        f"{_safe(summary['missing_source'] or 0)}\n"
        f"Без medium: "
        f"{_safe(summary['missing_medium'] or 0)}\n"
        f"Без campaign: "
        f"{_safe(summary['missing_campaign'] or 0)}\n"
        f"Без content: "
        f"{_safe(summary['missing_content'] or 0)}\n\n"
        "<b>Последние заявки</b>"
    )

    blocks = [
        _format_missing_job(row)
        for row in job_rows
    ] or ["—"]

    await _send_html_blocks(
        message=message,
        header=header,
        blocks=blocks,
    )


@router.message(Command("utm_link"))
async def dispatcher_utm_link(
    message: Message,
) -> None:
    if message.from_user.id not in CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS:
        await message.answer(
            "Команда доступна только диспетчеру CargoPT."
        )
        return

    parts = (message.text or "").split()

    if len(parts) not in {5, 6}:
        await message.answer(
            "Формат: /utm_link "
            "<pt|en|ru> <source> <medium> "
            "<campaign> [content]"
        )
        return

    try:
        link = _build_utm_link(
            locale=parts[1],
            source=parts[2],
            medium=parts[3],
            campaign=parts[4],
            content=(
                parts[5]
                if len(parts) == 6
                else None
            ),
        )
    except ValueError as exc:
        await message.answer(
            f"Не удалось создать ссылку: {_safe(exc)}",
            parse_mode="HTML",
        )
        return

    await message.answer(
        "<b>UTM-ссылка CargoPT</b>\n"
        f"<code>{_safe(link)}</code>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
