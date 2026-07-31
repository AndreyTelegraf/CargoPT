from datetime import UTC
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from aiogram import F
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove

from app.bot.handlers.regions import regions_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.db.session import async_session_maker
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.services.carrier_public_profile import LOGO_DIRECTORY
from app.services.carrier_public_profile import missing_public_profile_fields


router = Router()


def publication_consent_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Разрешаю публикацию")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


async def _prompt_next_missing_field(message: Message, state: FSMContext, carrier) -> None:
    missing = missing_public_profile_fields(carrier)
    update_only = bool((await state.get_data()).get("profile_update_only"))

    if "public_name" in missing:
        await state.set_state(CarrierOnboardingStates.public_name)
        await message.answer(
            "Укажите полное название компании или публичное имя — точно так, "
            "как его должны видеть клиенты CargoPT.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "experience_since_year" in missing:
        await state.set_state(CarrierOnboardingStates.experience_since_year)
        await message.answer(
            "С какого года вы занимаетесь грузовыми перевозками?\n\n"
            "Отправьте год четырьмя цифрами, например: 2018.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "logo" in missing:
        await state.set_state(CarrierOnboardingStates.logo)
        await message.answer(
            "Пришлите логотип компании или рабочее фото.\n\n"
            "Лучше использовать квадратное изображение. Отправьте его как фото "
            "или как файл JPG, PNG либо WEBP.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "publication_consent" in missing:
        await state.set_state(CarrierOnboardingStates.publication_consent)
        await message.answer(
            "Разрешаете CargoPT показывать название, изображение, стаж и регионы "
            "работы в вашей публичной карточке перевозчика?",
            reply_markup=publication_consent_keyboard(),
        )
        return

    if "operating_regions" in missing:
        await state.update_data(selected_regions=[])
        await state.set_state(CarrierOnboardingStates.operating_regions)
        await message.answer(
            "Выберите регионы работы и нажмите «Готово».",
            reply_markup=regions_keyboard(),
        )
        return

    if update_only:
        await state.clear()
        await message.answer(
            "Профиль дополнен. Новые сведения будут использоваться в карточке "
            "перевозчика CargoPT.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(selected_regions=[])
    await state.set_state(CarrierOnboardingStates.operating_regions)
    await message.answer(
        "Шаг 5 из 10. Регионы работы.\n\n"
        "В каких регионах Португалии вы работаете?\n\n"
        "Можно выбрать несколько регионов. Когда закончите, нажмите «Готово».",
        reply_markup=regions_keyboard(),
    )


async def start_public_profile_flow(
    message: Message,
    state: FSMContext,
    carrier,
    *,
    update_only: bool,
) -> None:
    await state.clear()
    await state.update_data(
        carrier_id=carrier.id,
        company_name=carrier.company_name,
        contact_name=carrier.contact_name,
        profile_update_only=update_only,
        public_name=carrier.public_name,
        experience_since_year=carrier.experience_since_year,
        logo_file_name=carrier.logo_file_name,
        publication_consent=carrier.publication_consent_at is not None,
    )
    await _prompt_next_missing_field(message, state, carrier)


@router.message(Command("profile"))
async def carrier_profile_command(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.get_carrier_by_telegram_user_id(message.from_user.id)
        if carrier is None or carrier.status == CarrierStatus.REJECTED:
            await message.answer("Профиль перевозчика не найден.")
            return
        if message.from_user.username:
            await repository.update_carrier_telegram_username(
                carrier.id,
                message.from_user.username,
            )
        await session.commit()

    await start_public_profile_flow(message, state, carrier, update_only=True)


@router.message(CarrierOnboardingStates.public_name, F.text)
async def public_name(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 2 or len(value) > 100:
        await message.answer("Название должно содержать от 2 до 100 символов.")
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        service = CarrierOnboardingService(CarrierRepository(session))
        carrier = await service.save_public_name(data["carrier_id"], value)
        await session.commit()
    await state.update_data(public_name=value)
    await _prompt_next_missing_field(message, state, carrier)


@router.message(CarrierOnboardingStates.experience_since_year, F.text)
async def experience_since_year(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    current_year = datetime.now(UTC).year
    if not raw.isdigit() or not 1950 <= int(raw) <= current_year:
        await message.answer(
            f"Отправьте год четырьмя цифрами — от 1950 до {current_year}."
        )
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        service = CarrierOnboardingService(CarrierRepository(session))
        carrier = await service.save_experience_since_year(
            data["carrier_id"],
            int(raw),
        )
        await session.commit()
    await state.update_data(experience_since_year=int(raw))
    await _prompt_next_missing_field(message, state, carrier)


def _image_source(message: Message):
    if message.photo:
        return message.photo[-1], ".jpg"
    document = message.document
    if document and document.mime_type in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        extension = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }[document.mime_type]
        return document, extension
    return None


@router.message(CarrierOnboardingStates.logo)
async def carrier_logo(message: Message, state: FSMContext) -> None:
    source = _image_source(message)
    if source is None:
        await message.answer("Пришлите изображение в формате JPG, PNG или WEBP.")
        return
    telegram_file, extension = source
    if telegram_file.file_size and telegram_file.file_size > 10 * 1024 * 1024:
        await message.answer("Изображение должно быть не больше 10 МБ.")
        return

    data = await state.get_data()
    carrier_id = int(data["carrier_id"])
    LOGO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    final_name = f"carrier_{carrier_id}{extension}"
    final_path = LOGO_DIRECTORY / final_name
    temporary_path = LOGO_DIRECTORY / f".carrier_{carrier_id}_{uuid4().hex}.tmp"

    try:
        await message.bot.download(telegram_file, destination=temporary_path)
        if not temporary_path.is_file() or temporary_path.stat().st_size == 0:
            raise ValueError("empty downloaded image")
        temporary_path.replace(final_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        await message.answer(
            "Не удалось сохранить изображение. Попробуйте отправить его ещё раз."
        )
        return

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        previous = await repository.get_carrier_by_id(carrier_id)
        previous_name = previous.logo_file_name if previous else None
        service = CarrierOnboardingService(repository)
        carrier = await service.save_logo_file_name(carrier_id, final_name)
        await session.commit()

    if previous_name and previous_name != final_name:
        previous_path = LOGO_DIRECTORY / Path(previous_name).name
        if previous_path.parent == LOGO_DIRECTORY and previous_path != final_path:
            previous_path.unlink(missing_ok=True)

    await state.update_data(logo_file_name=final_name)
    await _prompt_next_missing_field(message, state, carrier)


@router.message(
    CarrierOnboardingStates.publication_consent,
    F.text == "Разрешаю публикацию",
)
async def publication_consent(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    async with async_session_maker() as session:
        service = CarrierOnboardingService(CarrierRepository(session))
        carrier = await service.record_publication_consent(data["carrier_id"])
        await session.commit()
    await state.update_data(publication_consent=True)
    await _prompt_next_missing_field(message, state, carrier)


@router.message(CarrierOnboardingStates.publication_consent)
async def publication_consent_invalid(message: Message) -> None:
    await message.answer(
        "Для продолжения нажмите «Разрешаю публикацию». Если вы не хотите "
        "публиковать данные, свяжитесь с администратором CargoPT.",
        reply_markup=publication_consent_keyboard(),
    )
