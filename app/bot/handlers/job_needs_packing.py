from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import yes_no_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService

router = Router()


@router.message(JobRequestStates.needs_packing, F.text.in_(["Да", "Нет"]))
async def job_needs_packing(
    message: Message,
    state: FSMContext,
) -> None:
    needs_packing = message.text == "Да"

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_needs_packing(
            job_id=job_id,
            needs_packing=needs_packing,
        )

        await session.commit()

    await state.set_state(JobRequestStates.needs_tail_lift)

    await message.answer(
        "Нужен ли гидроборт?\n\n"
        "Гидроборт — это подъёмная платформа сзади грузовика для тяжёлых грузов.\n\n"
        "Выберите «Да», если груз невозможно безопасно поднять вручную: сейф, станок, палета, промышленное оборудование.\n\n"
        "Для коробок, мебели и большинства домашних переездов обычно выбирают «Нет».\n\n"
        "Важно: выбор «Да» значительно сокращает количество доступных перевозчиков.",
        reply_markup=yes_no_keyboard(),
    )
