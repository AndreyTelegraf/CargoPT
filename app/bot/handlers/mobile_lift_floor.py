from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.services.input_normalization import parse_first_int

router = Router()


@router.message(CarrierOnboardingStates.mobile_lift_max_floor)
async def mobile_lift_floor(
    message: Message,
    state: FSMContext,
) -> None:

    try:
        floor = parse_first_int(message.text)
    except Exception:
        await message.answer(text(await get_carrier_locale(state), "floor_invalid"))
        return

    if floor < 0:
        await message.answer(text(await get_carrier_locale(state), "floor_invalid"))
        return

    await state.update_data(
        mobile_lift_max_floor=floor
    )

    await state.set_state(CarrierOnboardingStates.mobile_lift_max_weight_kg)

    await message.answer(
        text(await get_carrier_locale(state), "mobile_lift_weight_prompt")
    )
