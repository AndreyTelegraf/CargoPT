from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import parse_yes_no
from app.bot.carrier_locale import text
from app.bot.carrier_locale import yes_no_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.domain.carrier_profile_step import CarrierProfileStep

router = Router()


@router.message(
    CarrierOnboardingStates.assembly_required,
    F.text,
)
async def assembly_required(
    message: Message,
    state: FSMContext,
) -> None:

    locale = await get_carrier_locale(state)
    assembly_required = parse_yes_no(message.text, locale)
    if assembly_required is None:
        await message.answer(text(locale, "yes_no_invalid"), reply_markup=yes_no_keyboard(locale))
        return

    data = await state.get_data()
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        await service.save_assembly_required(
            carrier_id=carrier_id,
            value=assembly_required,
        )

        await service.advance_profile_step(
            carrier_id=carrier_id,
            step=CarrierProfileStep.PACKING_REQUIRED,
        )

        await session.commit()

    await state.update_data(
        assembly_required=assembly_required
    )

    await state.set_state(
        CarrierOnboardingStates.packing_required
    )

    await message.answer(
        text(locale, "packing_prompt"),
        reply_markup=yes_no_keyboard(locale),
    )
