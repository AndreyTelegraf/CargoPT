from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import loaders_keyboard

from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.services.input_normalization import parse_first_float
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


@router.message(JobRequestStates.estimated_volume_m3)
async def job_estimated_volume(
    message: Message,
    state: FSMContext,
) -> None:
    raw_value = (message.text or "").strip()

    volume_map = {
        "до 3 м³": 3.0,
        "до 10 м³": 10.0,
        "до 18 м³": 18.0,
        "до 35 м³": 35.0,
        "Не знаю": 0.0,
    }

    if raw_value in volume_map:
        value = volume_map[raw_value]
    else:
        try:
            value = parse_first_float(raw_value)
        except ValueError:
            await message.answer("Выберите вариант кнопкой или укажите объём числом в м³.")
            return

    if value < 0:
        await message.answer("Объём не может быть отрицательным.")
        return

    estimated_volume_m3 = value or None

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_estimated_volume(
            job_id=job_id,
            estimated_volume_m3=estimated_volume_m3,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="required_loaders")
    await state.set_state(JobRequestStates.required_loaders)

    await message.answer(
        "Сколько грузчиков нужно?\n\n"
        "0 — если перевозка только машиной.\n"
        "1–2 — обычная погрузка мебели и коробок.\n"
        "3+ — тяжёлые предметы, этажи без лифта или большой объём.",
        reply_markup=loaders_keyboard(),
    )
