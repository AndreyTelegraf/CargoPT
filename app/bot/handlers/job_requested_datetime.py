from datetime import UTC
from datetime import datetime
from datetime import timedelta

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import support_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.domain.requested_date import PORTUGAL_TIMEZONE
from app.domain.requested_date import is_requested_date_in_past
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


def _parse_requested_datetime(
    raw_text: str,
    *,
    now: datetime | None = None,
) -> datetime | None:
    value = raw_text.strip()

    current = now or datetime.now(PORTUGAL_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(PORTUGAL_TIMEZONE)

    if value == "Сегодня":
        return _default_time_for_date(current, current).astimezone(UTC)

    if value == "Завтра":
        return (current + timedelta(days=1)).replace(
            hour=12,
            minute=0,
            second=0,
            microsecond=0,
        ).astimezone(UTC)

    if value == "В ближайшие дни":
        return (current + timedelta(days=3)).replace(
            hour=12,
            minute=0,
            second=0,
            microsecond=0,
        ).astimezone(UTC)

    if value == "Укажу дату текстом":
        return None

    for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%y %H:%M", "%d.%m %H:%M", "%d.%m.%Y", "%d.%m.%y", "%d.%m"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue

        if fmt in {"%d.%m %H:%M", "%d.%m"}:
            parsed = parsed.replace(year=current.year)

        if fmt in {"%d.%m.%Y", "%d.%m.%y", "%d.%m"}:
            parsed = _default_time_for_date(
                parsed.replace(tzinfo=PORTUGAL_TIMEZONE),
                current,
            ).replace(tzinfo=None)

        return parsed.replace(tzinfo=PORTUGAL_TIMEZONE).astimezone(UTC)

    return None


def _default_time_for_date(
    requested: datetime,
    current: datetime,
) -> datetime:
    midday = requested.replace(hour=12, minute=0, second=0, microsecond=0)
    if midday.date() != current.date() or midday > current:
        return midday

    next_hour = (current + timedelta(hours=1)).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    return next_hour


@router.message(JobRequestStates.requested_datetime)
async def job_requested_datetime(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()

    requested_date = _parse_requested_datetime(raw_text)

    if raw_text == "Укажу дату текстом" or requested_date is None:
        await message.answer(
            "Напишите дату и время перевозки текстом.\n\n"
            "Примеры:\n"
            "24.06 10:00\n"
            "24.06.2026 15:30\n"
            "24.06 — если точное время пока не важно.",
            reply_markup=support_keyboard(),
        )
        return

    if is_requested_date_in_past(requested_date):
        await message.answer(
            "Дата и время перевозки не могут быть в прошлом. "
            "Укажите будущее время.",
            reply_markup=support_keyboard(),
        )
        return

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_requested_date(
            job_id=job_id,
            requested_date=requested_date,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="item_description")
    await state.set_state(JobRequestStates.item_description)

    await message.answer(
        "Что нужно перевезти?\n\n"
        "Опишите груз простыми словами: например, «диван 2 метра, 10 коробок, стиральная машина».\n"
        "Если есть хрупкие, тяжёлые или нестандартные вещи — напишите это здесь.",
        reply_markup=support_keyboard(),
    )
