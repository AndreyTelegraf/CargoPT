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
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import normalize_carrier_locale
from app.bot.carrier_locale import single_button_keyboard
from app.bot.carrier_locale import text
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.db.session import async_session_maker
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.services.carrier_public_profile import LOGO_DIRECTORY
from app.services.carrier_public_profile import missing_public_profile_fields


router = Router()


def publication_consent_keyboard(locale: str = "ru") -> ReplyKeyboardMarkup:
    return single_button_keyboard(locale, "allow_publication")


async def _prompt_next_missing_field(message: Message, state: FSMContext, carrier) -> None:
    missing = missing_public_profile_fields(carrier)
    data = await state.get_data()
    update_only = bool(data.get("profile_update_only"))
    locale = normalize_carrier_locale(data.get("carrier_locale"))

    if "public_name" in missing:
        await state.set_state(CarrierOnboardingStates.public_name)
        await message.answer(
            text(locale, "public_name_prompt"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "experience_since_year" in missing:
        await state.set_state(CarrierOnboardingStates.experience_since_year)
        await message.answer(
            text(locale, "experience_prompt"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "logo" in missing:
        await state.set_state(CarrierOnboardingStates.logo)
        await message.answer(
            text(locale, "logo_prompt"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    if "publication_consent" in missing:
        await state.set_state(CarrierOnboardingStates.publication_consent)
        await message.answer(
            text(locale, "consent_prompt"),
            reply_markup=publication_consent_keyboard(locale),
        )
        return

    if "operating_regions" in missing:
        await state.update_data(selected_regions=[])
        await state.set_state(CarrierOnboardingStates.operating_regions)
        await message.answer(
            text(locale, "regions_short_prompt"),
            reply_markup=regions_keyboard(locale=locale),
        )
        return

    if update_only:
        await state.clear()
        await message.answer(
            text(locale, "profile_updated"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    await state.update_data(selected_regions=[])
    await state.set_state(CarrierOnboardingStates.operating_regions)
    await message.answer(
        text(locale, "regions_step_prompt"),
        reply_markup=regions_keyboard(locale=locale),
    )


async def start_public_profile_flow(
    message: Message,
    state: FSMContext,
    carrier,
    *,
    update_only: bool,
    preferred_locale: str | None = None,
) -> None:
    existing_data = await state.get_data()
    locale = preferred_locale or existing_data.get("carrier_locale") or carrier.preferred_locale
    if locale is None:
        from app.bot.handlers.invite import prompt_carrier_language

        await prompt_carrier_language(
            message,
            state,
            carrier,
            next_action="profile",
            update_only=update_only,
        )
        return
    locale = normalize_carrier_locale(locale)
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
        carrier_locale=locale,
    )
    await _prompt_next_missing_field(message, state, carrier)


@router.message(Command("profile"))
async def carrier_profile_command(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.get_carrier_by_telegram_user_id(message.from_user.id)
        if carrier is None or carrier.status == CarrierStatus.REJECTED:
            locale = normalize_carrier_locale(message.from_user.language_code)
            await message.answer(text(locale, "profile_not_found"))
            return
        if message.from_user.username:
            await repository.update_carrier_telegram_username(
                carrier.id,
                message.from_user.username,
            )
        await session.commit()

    await start_public_profile_flow(message, state, carrier, update_only=True)


@router.message(Command("language"))
async def carrier_language_command(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        carrier = await CarrierRepository(session).get_carrier_by_telegram_user_id(
            message.from_user.id
        )
    if carrier is None or carrier.status == CarrierStatus.REJECTED:
        locale = normalize_carrier_locale(message.from_user.language_code)
        await message.answer(text(locale, "profile_not_found"))
        return
    from app.bot.handlers.invite import prompt_carrier_language

    await prompt_carrier_language(
        message,
        state,
        carrier,
        next_action="profile",
        update_only=True,
    )


@router.message(CarrierOnboardingStates.public_name, F.text)
async def public_name(message: Message, state: FSMContext) -> None:
    value = (message.text or "").strip()
    if len(value) < 2 or len(value) > 100:
        await message.answer(text(await get_carrier_locale(state), "public_name_invalid"))
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
            text(await get_carrier_locale(state), "experience_invalid", current_year=current_year)
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
        await message.answer(text(await get_carrier_locale(state), "logo_invalid"))
        return
    telegram_file, extension = source
    if telegram_file.file_size and telegram_file.file_size > 10 * 1024 * 1024:
        await message.answer(text(await get_carrier_locale(state), "logo_too_large"))
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
            text(await get_carrier_locale(state), "logo_save_error")
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
    F.text,
)
async def publication_consent(message: Message, state: FSMContext) -> None:
    locale = await get_carrier_locale(state)
    if message.text != text(locale, "allow_publication"):
        await message.answer(
            text(locale, "consent_invalid"),
            reply_markup=publication_consent_keyboard(locale),
        )
        return
    data = await state.get_data()
    async with async_session_maker() as session:
        service = CarrierOnboardingService(CarrierRepository(session))
        carrier = await service.record_publication_consent(data["carrier_id"])
        await session.commit()
    await state.update_data(publication_consent=True)
    await _prompt_next_missing_field(message, state, carrier)
