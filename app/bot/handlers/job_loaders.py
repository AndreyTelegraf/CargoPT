from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import phone_skip_keyboard

from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.services.input_normalization import parse_first_int
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


@router.message(JobRequestStates.required_loaders)
async def job_required_loaders(
    message: Message,
    state: FSMContext,
) -> None:
    raw_value = (message.text or "").strip()

    loader_map = {
        "Не знаю": 0,
        "4+": 4,
    }

    if raw_value in loader_map:
        value = loader_map[raw_value]
    else:
        try:
            value = parse_first_int(raw_value)
        except ValueError:
            await message.answer("Выберите вариант кнопкой или укажите количество грузчиков числом.")
            return

    if value < 0:
        await message.answer("Количество грузчиков не может быть отрицательным.")
        return

    required_loaders = value or None

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_required_loaders(
            job_id=job_id,
            required_loaders=required_loaders,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="contact_phone")
    await state.set_state(JobRequestStates.contact_phone)

    await message.answer(
        "Контактный телефон для перевозчика.\n\n"
        "Telegram username подтягивается автоматически. Телефон нужен как запасной канал связи, если водитель не сможет быстро найти вас в Telegram.\n"
        "Отправьте номер или нажмите «Не указывать телефон».",
        reply_markup=phone_skip_keyboard(),
    )
