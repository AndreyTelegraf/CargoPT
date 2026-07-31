from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.vehicle_type import vehicle_type_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates

router = Router()


@router.message(CarrierOnboardingStates.vehicle_count, F.text.regexp(r"^[1-9][0-9]*$"))
async def vehicle_count(
    message: Message,
    state: FSMContext,
) -> None:
    count = int(message.text)

    await state.update_data(
        vehicle_count=count,
        current_vehicle_index=1,
        vehicles=[],
        vehicle_type=None,
        payload_kg=None,
        volume_m3=None,
        has_tail_lift=None,
        has_crane=None,
        has_mobile_lift=None,
        mobile_lift_max_floor=None,
        mobile_lift_max_weight_kg=None,
        crane_max_weight_kg=None,
        crane_max_reach_m=None,
        max_loaders=None,
    )

    await state.set_state(CarrierOnboardingStates.vehicle_type)

    await message.answer(
        f"Шаг 7 из 10. Автомобиль 1 из {count}.\n\n"
        "Выберите тип автомобиля.",
        reply_markup=vehicle_type_keyboard(),
    )

print("VEHICLE_COUNT_HANDLER_LOADED")
