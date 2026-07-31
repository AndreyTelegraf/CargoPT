from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states.carrier_onboarding import CarrierOnboardingStates

router = Router()


@router.message(CarrierOnboardingStates.has_mobile_lift, F.text.in_(["Да", "Нет"]))
async def mobile_lift(
    message: Message,
    state: FSMContext,
) -> None:

    has_mobile_lift = message.text == "Да"

    await state.update_data(
        has_mobile_lift=has_mobile_lift
    )

    if has_mobile_lift:
        await state.set_state(CarrierOnboardingStates.mobile_lift_max_floor)
        await message.answer(
            "На какой максимальный этаж может подавать мобильный лифт?"
        )
        return

    await state.update_data(
        mobile_lift_max_floor=None,
        mobile_lift_max_weight_kg=None,
    )

    await state.set_state(CarrierOnboardingStates.max_loaders)

    await message.answer(
        "Шаг 8 из 10. Команда.\n\n"
        "Сколько грузчиков одновременно вы можете предоставить на один заказ?"
    )
