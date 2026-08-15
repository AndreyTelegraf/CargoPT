from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import parse_yes_no
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard

router = Router()


@router.message(CarrierOnboardingStates.has_mobile_lift, F.text)
async def mobile_lift(
    message: Message,
    state: FSMContext,
) -> None:

    locale = await get_carrier_locale(state)
    has_mobile_lift = parse_yes_no(message.text, locale)
    if has_mobile_lift is None:
        await message.answer(text(locale, "yes_no_invalid"), reply_markup=yes_no_keyboard(locale))
        return

    await state.update_data(
        has_mobile_lift=has_mobile_lift
    )

    if has_mobile_lift:
        await state.set_state(CarrierOnboardingStates.mobile_lift_max_floor)
        await message.answer(
            text(locale, "mobile_lift_floor_prompt")
        )
        return

    await state.update_data(
        mobile_lift_max_floor=None,
        mobile_lift_max_weight_kg=None,
    )

    await state.set_state(CarrierOnboardingStates.max_loaders)

    await message.answer(
        text(locale, "loaders_prompt")
    )
