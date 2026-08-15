from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard
from app.db.session import async_session_maker
from app.domain.carrier_profile_step import CarrierProfileStep
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.services.input_normalization import parse_first_float

router = Router()


@router.message(CarrierOnboardingStates.volume_m3)
async def volume_m3(
    message: Message,
    state: FSMContext,
) -> None:

    try:
        volume = parse_first_float(message.text)
    except Exception:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    if volume <= 0:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    await state.update_data(
        volume_m3=volume
    )

    data = await state.get_data()
    locale = await get_carrier_locale(state)

    if "assembly_required" in data and "packing_required" in data:
        await state.set_state(CarrierOnboardingStates.has_tail_lift)
        await message.answer(
            text(locale, "tail_lift_prompt"),
            reply_markup=yes_no_keyboard(locale),
        )
        return

    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)
        await service.advance_profile_step(
            carrier_id=carrier_id,
            step=CarrierProfileStep.ASSEMBLY_REQUIRED,
        )
        await session.commit()

    await state.set_state(CarrierOnboardingStates.assembly_required)

    await message.answer(
        text(locale, "assembly_prompt"),
        reply_markup=yes_no_keyboard(locale),
    )
