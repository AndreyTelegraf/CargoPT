from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import language_keyboard
from app.bot.carrier_locale import locale_from_language_button
from app.bot.carrier_locale import normalize_carrier_locale
from app.bot.carrier_locale import single_button_keyboard
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.domain.carrier_status import CarrierStatus
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.handlers.carrier_public_profile import start_public_profile_flow

router = Router()


def carrier_welcome_keyboard(locale: str = "ru"):
    return single_button_keyboard(locale, "start")


def carrier_yes_no_keyboard(locale: str = "ru"):
    return yes_no_keyboard(locale)


async def prompt_carrier_language(
    message: Message,
    state: FSMContext,
    carrier,
    *,
    next_action: str,
    update_only: bool = False,
) -> None:
    await state.clear()
    await state.update_data(
        carrier_id=carrier.id,
        company_name=carrier.company_name,
        contact_name=carrier.contact_name,
        carrier_locale_next=next_action,
        profile_update_only=update_only,
    )
    await state.set_state(CarrierOnboardingStates.language)
    await message.answer(
        "Escolha o idioma / Choose your language / Выберите язык",
        reply_markup=language_keyboard(),
    )


@router.message(CarrierOnboardingStates.language, F.text)
async def carrier_language(message: Message, state: FSMContext) -> None:
    locale = locale_from_language_button(message.text)
    if locale is None:
        await message.answer(
            "Escolha o idioma / Choose your language / Выберите язык",
            reply_markup=language_keyboard(),
        )
        return

    data = await state.get_data()
    carrier_id = int(data["carrier_id"])
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.update_preferred_locale(carrier_id, locale)
        await session.commit()

    await state.update_data(carrier_locale=locale)
    if data.get("carrier_locale_next") == "welcome":
        await state.set_state(CarrierOnboardingStates.welcome)
        await message.answer(
            text(locale, "welcome", company_name=carrier.company_name),
            reply_markup=carrier_welcome_keyboard(locale),
        )
        return

    await start_public_profile_flow(
        message,
        state,
        carrier,
        update_only=bool(data.get("profile_update_only")),
        preferred_locale=locale,
    )


@router.message(CommandStart(deep_link=True))
async def invite_start(message: Message, state: FSMContext) -> None:
    payload = (message.text or "").split(maxsplit=1)

    if len(payload) != 2:
        locale = normalize_carrier_locale(message.from_user.language_code)
        await message.answer(
            text(locale, "no_invitation")
        )
        return

    token = payload[1].strip()

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        existing_carrier = await repository.get_carrier_by_telegram_user_id(
            message.from_user.id
        )
        if token == "profile":
            if existing_carrier is None and message.from_user.username:
                username_carrier = await repository.get_carrier_by_username(
                    message.from_user.username
                )
                if (
                    username_carrier is not None
                    and username_carrier.telegram_user_id is None
                    and username_carrier.status != CarrierStatus.REJECTED
                ):
                    existing_carrier = await repository.bind_carrier_telegram_identity(
                        username_carrier.id,
                        telegram_user_id=message.from_user.id,
                        telegram_username=message.from_user.username,
                    )
            if existing_carrier is None or existing_carrier.status == CarrierStatus.REJECTED:
                locale = normalize_carrier_locale(message.from_user.language_code)
                await message.answer(text(locale, "profile_not_found"))
                return
            if message.from_user.username:
                await repository.update_carrier_telegram_username(
                    existing_carrier.id,
                    message.from_user.username,
                )
            await session.commit()
            await start_public_profile_flow(
                message,
                state,
                existing_carrier,
                update_only=True,
            )
            return
        if (
            existing_carrier is not None
            and existing_carrier.status == CarrierStatus.INVITED
        ):
            await session.commit()
            await start_public_profile_flow(
                message,
                state,
                existing_carrier,
                update_only=False,
            )
            return

        if existing_carrier is not None:
            await session.commit()
            await state.clear()
            await message.answer(
                text(
                    existing_carrier.preferred_locale
                    or normalize_carrier_locale(message.from_user.language_code),
                    "already_registered",
                )
            )
            return

        try:
            invite = await service.claim_invite_token(
                token=token,
                telegram_user_id=message.from_user.id,
                telegram_username=message.from_user.username,
            )

            carrier = await repository.get_carrier_by_id(invite.carrier_id)

            if carrier is None:
                raise ValueError("carrier not found")

            await session.commit()

        except Exception:
            await session.rollback()
            locale = normalize_carrier_locale(message.from_user.language_code)
            await message.answer(
                text(locale, "invalid_invitation")
            )
            return

    await prompt_carrier_language(
        message,
        state,
        carrier,
        next_action="welcome",
    )


@router.message(CarrierOnboardingStates.welcome, F.text)
async def carrier_welcome_start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    locale = await get_carrier_locale(state)
    if message.text != text(locale, "start"):
        await message.answer(
            text(locale, "welcome", company_name=data.get("company_name", "")),
            reply_markup=carrier_welcome_keyboard(locale),
        )
        return
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        carrier = await CarrierRepository(session).get_carrier_by_id(carrier_id)

    if carrier is None:
        await message.answer(text(locale, "questionnaire_not_found"))
        return

    await start_public_profile_flow(
        message,
        state,
        carrier,
        update_only=False,
        preferred_locale=locale,
    )
