from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import floor_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.bot.handlers.job_request_persistence import persist_draft_step
from app.services.request_update import RequestUpdateService

router = Router()


@router.message(JobRequestStates.dropoff_address, F.text | F.location)
async def job_dropoff_address(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    latitude = None
    longitude = None

    if message.location:
        latitude = message.location.latitude
        longitude = message.location.longitude
        raw_text = f"Telegram location: {latitude}, {longitude}"

    if not raw_text or raw_text.startswith("/"):
        await message.answer("Укажите адрес, ссылку на Google Maps или отправьте геолокацию Telegram.")
        return

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        address = await service.add_address(
            job_id=job_id,
            kind="dropoff",
            raw_text=raw_text,
            latitude=latitude,
            longitude=longitude,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="dropoff_details")
    await state.update_data(dropoff_address_id=address.id)
    await state.set_state(JobRequestStates.dropoff_details)

    await message.answer(
        "Этаж выгрузки.\n\n"
        "Выберите этаж кнопкой или введите число от 0 до 24. Если это подвал — нажмите «Подвал».",
        reply_markup=floor_keyboard(),
    )
