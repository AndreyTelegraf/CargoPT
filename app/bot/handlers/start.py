from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.job_start import start_job_request
from app.db.session import async_session_maker
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.bot.handlers.carrier_public_profile import start_public_profile_flow
from app.services.carrier_public_profile import missing_public_profile_fields
from app.bot.carrier_locale import normalize_carrier_locale
from app.bot.carrier_locale import text

router = Router()


def build_existing_carrier_start_text(carrier, locale: str = "ru") -> str:
    if carrier.status == CarrierStatus.PENDING_MODERATION:
        return text(locale, "status_pending")

    if carrier.status == CarrierStatus.ACTIVE:
        return text(locale, "status_active")

    if carrier.status == CarrierStatus.PROFILE_COMPLETED:
        return text(locale, "status_completed")

    return text(locale, "status_bound")


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.get_carrier_by_telegram_user_id(message.from_user.id)
        if carrier is not None and message.from_user.username:
            await repository.update_carrier_telegram_username(
                carrier.id,
                message.from_user.username,
            )
            await session.commit()

    if carrier is not None and carrier.status == CarrierStatus.INVITED:
        await start_public_profile_flow(
            message,
            state,
            carrier,
            update_only=False,
        )
        return

    if carrier is not None and carrier.status != CarrierStatus.REJECTED:
        if missing_public_profile_fields(carrier):
            await start_public_profile_flow(
                message,
                state,
                carrier,
                update_only=True,
            )
            return
        await state.clear()
        locale = normalize_carrier_locale(
            carrier.preferred_locale or message.from_user.language_code
        )
        await message.answer(build_existing_carrier_start_text(carrier, locale))
        return

    await start_job_request(message, state)


@router.message(F.text == "Помощь")
async def help_placeholder(message: Message) -> None:
    await message.answer(
        "Поддержка CargoPT: https://t.me/andreytelegraf"
    )
