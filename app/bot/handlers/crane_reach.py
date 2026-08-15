from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.services.input_normalization import parse_first_int

router = Router()


@router.message(CarrierOnboardingStates.crane_reach_meters)
async def crane_reach(
    message: Message,
    state: FSMContext,
) -> None:

    try:
        reach = parse_first_int(message.text)
    except Exception:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    if reach <= 0:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    await state.update_data(
        crane_max_reach_m=reach
    )

    await state.set_state(CarrierOnboardingStates.has_mobile_lift)

    await message.answer(
        text(await get_carrier_locale(state), "mobile_lift_prompt"),
        reply_markup=yes_no_keyboard(await get_carrier_locale(state)),
    )
