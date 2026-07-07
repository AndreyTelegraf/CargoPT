import asyncio

from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import media_skip_keyboard
from app.bot.job_request_keyboards import volume_keyboard

from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService

router = Router()

_MEDIA_ACK_LOCKS: dict[tuple[int, int, str], asyncio.Lock] = {}


def _media_ack_lock_key(message: Message) -> tuple[int, int, str]:
    group_id = message.media_group_id or f"single:{message.message_id}"
    return message.chat.id, message.from_user.id, group_id


def _media_ack_lock(message: Message) -> asyncio.Lock:
    key = _media_ack_lock_key(message)
    lock = _MEDIA_ACK_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _MEDIA_ACK_LOCKS[key] = lock
    return lock


@router.message(JobRequestStates.media, F.photo | F.video | F.text)
async def job_media(
    message: Message,
    state: FSMContext,
) -> None:
    async with _media_ack_lock(message):
        data = await state.get_data()
        job_id = data["job_id"]

        media_type = None
        telegram_file_id = None
        caption = message.caption

        if message.photo:
            media_type = "photo"
            telegram_file_id = message.photo[-1].file_id
        elif message.video:
            media_type = "video"
            telegram_file_id = message.video.file_id
        elif (message.text or "").strip() in {"-", "Следующий шаг"}:
            await state.set_state(JobRequestStates.estimated_volume_m3)
            await message.answer(
                "Оцените примерный объём груза.\n\n"
                "Ориентир по машине:\n"
                "- до 3 м³ — несколько вещей или коробок;\n"
                "- до 10 м³ — маленький фургон;\n"
                "- до 18 м³ — большой фургон;\n"
                "- до 35 м³ — грузовик.\n\n"
                "Можно нажать кнопку или ввести число в м³.",
                reply_markup=volume_keyboard(),
            )
            return
        else:
            await message.answer("Пришлите фото или видео груза либо нажмите «Следующий шаг».")
            return

        async with async_session_maker() as session:
            repository = JobRepository(session)
            service = RequestUpdateService(job_repository=repository)

            await service.add_media(
                job_id=job_id,
                media_type=media_type,
                telegram_file_id=telegram_file_id,
                caption=caption,
            )

            await session.commit()

        await state.update_data(media_saved=True)

        if not data.get("media_ack_sent"):
            await state.update_data(media_ack_sent=True)
            await message.answer(
                "Медиа сохранено. Можете добавить ещё фото или видео либо нажать «Следующий шаг».",
                reply_markup=media_skip_keyboard(),
            )
