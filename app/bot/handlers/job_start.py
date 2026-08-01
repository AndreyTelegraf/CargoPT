from datetime import UTC
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.job_request_keyboards import client_start_keyboard
from app.bot.job_request_keyboards import comment_skip_keyboard
from app.bot.job_request_keyboards import datetime_keyboard
from app.bot.job_request_keyboards import floor_keyboard
from app.bot.job_request_keyboards import loaders_keyboard
from app.bot.job_request_keyboards import media_skip_keyboard
from app.bot.job_request_keyboards import phone_skip_keyboard
from app.bot.job_request_keyboards import support_keyboard
from app.bot.job_request_keyboards import username_ready_keyboard
from app.bot.job_request_keyboards import volume_keyboard
from app.bot.job_request_keyboards import whatsapp_keyboard
from app.bot.states.job_request import JobRequestStates
from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_draft import ClientBannedError
from app.services.request_draft import RequestDraftService

router = Router()


RESUME_PROMPTS = {
    "pickup_address": (
        JobRequestStates.pickup_address,
        "Укажите адрес загрузки: ссылка Google Maps, текстовый адрес или геолокация Telegram.",
        client_start_keyboard,
    ),
    "pickup_details": (
        JobRequestStates.pickup_details,
        "Укажите этаж загрузки: число от 0 до 24 или «Подвал».",
        floor_keyboard,
    ),
    "dropoff_address": (
        JobRequestStates.dropoff_address,
        "Укажите адрес выгрузки: ссылка Google Maps, текстовый адрес или геолокация Telegram.",
        support_keyboard,
    ),
    "dropoff_details": (
        JobRequestStates.dropoff_details,
        "Укажите этаж выгрузки: число от 0 до 24 или «Подвал».",
        floor_keyboard,
    ),
    "requested_datetime": (
        JobRequestStates.requested_datetime,
        "Когда нужна перевозка? Выберите вариант или напишите дату и время.",
        datetime_keyboard,
    ),
    "item_description": (
        JobRequestStates.item_description,
        "Опишите, что нужно перевезти.",
        support_keyboard,
    ),
    "media": (
        JobRequestStates.media,
        "Пришлите фото или видео груза либо нажмите «Следующий шаг».",
        media_skip_keyboard,
    ),
    "estimated_volume_m3": (
        JobRequestStates.estimated_volume_m3,
        "Оцените примерный объём груза в м³.",
        volume_keyboard,
    ),
    "required_loaders": (
        JobRequestStates.required_loaders,
        "Сколько грузчиков нужно?",
        loaders_keyboard,
    ),
    "contact_phone": (
        JobRequestStates.contact_phone,
        "Укажите контактный телефон или нажмите «Не указывать телефон».",
        phone_skip_keyboard,
    ),
    "contact_whatsapp": (
        JobRequestStates.contact_whatsapp,
        "Укажите WhatsApp или выберите один из вариантов.",
        whatsapp_keyboard,
    ),
    "comment": (
        JobRequestStates.comment,
        "Добавьте комментарий или нажмите «Без комментария».",
        comment_skip_keyboard,
    ),
}


USERNAME_TEXT = (
    "Перед созданием заявки нужен Telegram username.\n\n"
    "Он нужен, чтобы перевозчик мог связаться с вами после принятия заказа, "
    "а бот мог показать контакт без ручного копирования телефона.\n\n"
    "Как создать username:\n"
    "1. Откройте Telegram Settings / Настройки.\n"
    "2. Нажмите Username / Имя пользователя.\n"
    "3. Придумайте имя латиницей, например cargo_client_123.\n"
    "4. Вернитесь сюда и нажмите «Готово, username создан»."
)


async def _create_job_and_ask_pickup(
    message: Message,
    state: FSMContext,
) -> None:
    async with async_session_maker() as session:
        repository = JobRepository(session)
        draft_service = RequestDraftService(job_repository=repository)

        try:
            result = await draft_service.create_or_reuse_telegram_draft(
                client_telegram_user_id=message.from_user.id,
                client_telegram_username=message.from_user.username,
            )
        except ClientBannedError:
            await message.answer(
                "Вы временно отключены от создания заявок CargoPT. "
                "По вопросам: https://t.me/andreytelegraf"
            )
            await session.rollback()
            return

        job = result.job
        addresses = await repository.list_addresses_by_job(job.id)
        await session.commit()

    resume_step = result.resume_step
    state_config = RESUME_PROMPTS.get(resume_step, RESUME_PROMPTS["pickup_address"])
    resume_state, prompt, keyboard_factory = state_config

    state_data = {"job_id": job.id}
    pickup = next((address for address in addresses if address.kind == "pickup"), None)
    dropoff = next(
        (address for address in addresses if address.kind in {"dropoff", "delivery"}),
        None,
    )
    if pickup is not None:
        state_data["pickup_address_id"] = pickup.id
    if dropoff is not None:
        state_data["dropoff_address_id"] = dropoff.id
    if job.client_phone:
        state_data["client_phone"] = job.client_phone

    await state.set_state(resume_state)
    await state.update_data(**state_data)

    if result.reused_existing_draft:
        prompt = (
            f"Продолжаем ранее начатую заявку #{job.id}.\n\n"
            f"{prompt}\n\n"
            "Чтобы отказаться от этого черновика и начать заново, используйте /new_job_fresh."
        )
    else:
        prompt = (
            "Начнём с места, где нужно забрать ваш груз.\n\n"
            "Вставьте ссылку на локацию из Google Maps или введите полный адрес."
        )

    await message.answer(prompt, reply_markup=keyboard_factory())


@router.message(Command("new_job"))
async def start_job_request(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.from_user.username:
        await state.set_state(JobRequestStates.telegram_username_missing)
        await message.answer(
            USERNAME_TEXT,
            reply_markup=username_ready_keyboard(),
        )
        return

    await _create_job_and_ask_pickup(message, state)


@router.message(Command("new_job_fresh"))
async def start_fresh_job_request(message: Message, state: FSMContext) -> None:
    if not message.from_user.username:
        await state.set_state(JobRequestStates.telegram_username_missing)
        await message.answer(USERNAME_TEXT, reply_markup=username_ready_keyboard())
        return

    async with async_session_maker() as session:
        repository = JobRepository(session)
        latest_draft = await repository.get_latest_draft_job_by_client_id(
            message.from_user.id
        )
        if latest_draft is not None:
            await repository.archive_draft(
                job_id=latest_draft.id,
                updated_at=datetime.now(UTC),
            )
        await session.commit()

    await state.clear()
    await _create_job_and_ask_pickup(message, state)


@router.message(JobRequestStates.telegram_username_missing)
async def continue_after_username_created(
    message: Message,
    state: FSMContext,
) -> None:
    if not message.from_user.username:
        await message.answer(
            USERNAME_TEXT,
            reply_markup=username_ready_keyboard(),
        )
        return

    await _create_job_and_ask_pickup(message, state)
