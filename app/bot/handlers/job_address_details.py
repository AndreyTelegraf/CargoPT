from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import datetime_keyboard
from app.bot.job_request_keyboards import elevator_keyboard
from app.bot.job_request_keyboards import floor_keyboard
from app.bot.job_request_keyboards import support_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


def _parse_floor(raw_text: str) -> int:
    value = (raw_text or "").strip().casefold()

    if value in {"подвал", "-1"}:
        return -1

    try:
        floor = int(value)
    except ValueError as exc:
        raise ValueError("invalid floor") from exc

    if floor < 0 or floor > 24:
        raise ValueError("floor out of range")

    return floor


def _parse_elevator(raw_text: str) -> bool:
    value = (raw_text or "").strip().casefold()

    if value == "да":
        return True
    if value == "нет":
        return False

    raise ValueError("invalid elevator")


async def _save_address_details(
    *,
    state: FSMContext,
    address_id_key: str,
    floor_key: str,
    has_elevator: bool,
) -> None:
    data = await state.get_data()
    address_id = data[address_id_key]
    floor = data[floor_key]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_address_details(
            address_id=address_id,
            floor=floor,
            has_elevator=has_elevator,
        )

        await session.commit()


@router.message(JobRequestStates.pickup_details)
async def pickup_details(message: Message, state: FSMContext) -> None:
    try:
        floor = _parse_floor(message.text or "")
    except ValueError:
        await message.answer(
            "Выберите этаж кнопкой или введите число от 0 до 24. Если это подвал — нажмите «Подвал».",
            reply_markup=floor_keyboard(),
        )
        return

    await state.update_data(pickup_floor=floor)
    await state.set_state(JobRequestStates.pickup_elevator)

    await message.answer(
        "Есть ли лифт на загрузке?",
        reply_markup=elevator_keyboard(),
    )


@router.message(JobRequestStates.pickup_elevator)
async def pickup_elevator(message: Message, state: FSMContext) -> None:
    try:
        has_elevator = _parse_elevator(message.text or "")
    except ValueError:
        await message.answer("Выберите «Да» или «Нет».", reply_markup=elevator_keyboard())
        return

    await _save_address_details(
        state=state,
        address_id_key="pickup_address_id",
        floor_key="pickup_floor",
        has_elevator=has_elevator,
    )

    data = await state.get_data()
    await persist_draft_step(
        job_id=data["job_id"],
        draft_step="dropoff_address",
    )
    await state.set_state(JobRequestStates.dropoff_address)

    await message.answer(
        "Теперь место выгрузки.\n\n"
        "Вставьте ссылку на точку из Google Maps или введите полный адрес, "
        "например Rua Escura, 1, Porto, 4050-242",
        reply_markup=support_keyboard(),
    )


@router.message(JobRequestStates.dropoff_details)
async def dropoff_details(message: Message, state: FSMContext) -> None:
    try:
        floor = _parse_floor(message.text or "")
    except ValueError:
        await message.answer(
            "Выберите этаж кнопкой или введите число от 0 до 24. Если это подвал — нажмите «Подвал».",
            reply_markup=floor_keyboard(),
        )
        return

    await state.update_data(dropoff_floor=floor)
    await state.set_state(JobRequestStates.dropoff_elevator)

    await message.answer(
        "Есть ли лифт на выгрузке?",
        reply_markup=elevator_keyboard(),
    )


@router.message(JobRequestStates.dropoff_elevator)
async def dropoff_elevator(message: Message, state: FSMContext) -> None:
    try:
        has_elevator = _parse_elevator(message.text or "")
    except ValueError:
        await message.answer("Выберите «Да» или «Нет».", reply_markup=elevator_keyboard())
        return

    await _save_address_details(
        state=state,
        address_id_key="dropoff_address_id",
        floor_key="dropoff_floor",
        has_elevator=has_elevator,
    )

    data = await state.get_data()
    await persist_draft_step(
        job_id=data["job_id"],
        draft_step="requested_datetime",
    )
    await state.set_state(JobRequestStates.requested_datetime)

    await message.answer(
        "Когда нужна перевозка?\n\n"
        "Выберите быстрый вариант или напишите дату и время вручную.\n"
        "Примеры: 24.06 10:00, 24.06.2026 15:30.\n"
        "Если точное время пока не важно — напишите только дату.",
        reply_markup=datetime_keyboard(),
    )
