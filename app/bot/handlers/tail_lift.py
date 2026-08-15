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


@router.message(CarrierOnboardingStates.has_tail_lift, F.text)
async def tail_lift(
    message: Message,
    state: FSMContext,
) -> None:

    locale = await get_carrier_locale(state)
    value = parse_yes_no(message.text, locale)
    if value is None:
        await message.answer(text(locale, "yes_no_invalid"), reply_markup=yes_no_keyboard(locale))
        return
    await state.update_data(has_tail_lift=value)

    await state.set_state(CarrierOnboardingStates.has_crane)

    await message.answer(
        text(locale, "crane_prompt"),
        reply_markup=yes_no_keyboard(locale),
    )
