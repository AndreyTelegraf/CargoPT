from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import support_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


@router.message(JobRequestStates.item_description)
async def job_item_description(
    message: Message,
    state: FSMContext,
) -> None:
    description = (message.text or "").strip()

    if not description:
        await message.answer("Опишите груз коротким текстом.", reply_markup=support_keyboard())
        return

    data = await state.get_data()
    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.add_item(
            job_id=job_id,
            description=description,
            quantity=None,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="media")
    await state.set_state(JobRequestStates.media)

    from app.bot.job_request_keyboards import media_skip_keyboard

    await message.answer(
        "Пришлите фото или видео груза.\n\n"
        "Лучше снять так, чтобы перевозчик понял объём: общий вид, крупные предметы, коробки и проходы.\n"
        "Можно отправить одно фото или одно видео. Если медиа нет — нажмите «Пропустить медиа».",
        reply_markup=media_skip_keyboard(),
    )
