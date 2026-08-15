from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import parse_yes_no
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates

router = Router()


@router.message(CarrierOnboardingStates.has_crane, F.text)
async def crane(
    message: Message,
    state: FSMContext,
) -> None:

    locale = await get_carrier_locale(state)
    has_crane = parse_yes_no(message.text, locale)
    if has_crane is None:
        await message.answer(text(locale, "yes_no_invalid"), reply_markup=yes_no_keyboard(locale))
        return

    await state.update_data(
        has_crane=has_crane
    )

    if has_crane:
        await state.set_state(CarrierOnboardingStates.crane_max_weight_kg)
        await message.answer(
            text(locale, "crane_weight_prompt")
        )
        return

    await state.update_data(
        crane_max_weight_kg=None,
        crane_max_reach_m=None,
    )

    await state.set_state(CarrierOnboardingStates.has_mobile_lift)

    await message.answer(
        text(locale, "mobile_lift_prompt"),
        reply_markup=yes_no_keyboard(locale),
    )
