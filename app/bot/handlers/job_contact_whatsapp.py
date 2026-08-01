from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import comment_skip_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService
from app.bot.handlers.job_request_persistence import persist_draft_step

router = Router()


@router.message(JobRequestStates.contact_whatsapp)
async def job_contact_whatsapp(
    message: Message,
    state: FSMContext,
) -> None:
    raw_value = (message.text or "").strip()
    data = await state.get_data()
    phone = data.get("client_phone")

    if raw_value == "WhatsApp совпадает":
        whatsapp = phone
    elif raw_value in {"", "-", "Не указывать WhatsApp"}:
        whatsapp = None
    else:
        whatsapp = raw_value

    job_id = data["job_id"]

    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        await service.update_client_whatsapp(
            job_id=job_id,
            client_whatsapp=whatsapp,
        )

        await session.commit()

    await persist_draft_step(job_id=job_id, draft_step="comment")
    await state.set_state(JobRequestStates.comment)

    await message.answer(
        "Последний шаг: комментарий к заказу.\n\n"
        "Напишите всё, что поможет перевозчику: этаж, лифт, парковка, хрупкие вещи, узкий подъезд, удобное время.\n"
        "Если добавить нечего — нажмите «Без комментария».",
        reply_markup=comment_skip_keyboard(),
    )
