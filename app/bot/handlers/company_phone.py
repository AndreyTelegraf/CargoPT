from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text

router = Router()


@router.message(CarrierOnboardingStates.company_phone)
async def company_phone(
    message: Message,
    state: FSMContext,
) -> None:

    phone = (message.text or "").strip()

    if len(phone) < 6:
        await message.answer(text(await get_carrier_locale(state), "phone_prompt"))
        return

    await state.update_data(
        company_phone=phone
    )

    await state.set_state(CarrierOnboardingStates.company_email)

    await message.answer(
        text(await get_carrier_locale(state), "email_prompt")
    )
