from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.services.input_normalization import parse_first_int

router = Router()


@router.message(CarrierOnboardingStates.payload_kg)
async def payload_kg(
    message: Message,
    state: FSMContext,
) -> None:

    try:
        payload = parse_first_int(message.text)
    except Exception:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    if payload <= 0:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    await state.update_data(
        payload_kg=payload
    )

    await state.set_state(CarrierOnboardingStates.volume_m3)

    await message.answer(
        text(await get_carrier_locale(state), "volume_prompt")
    )
