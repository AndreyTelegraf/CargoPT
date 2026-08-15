from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.vehicle_type import vehicle_type_keyboard
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.services.input_normalization import parse_first_int

router = Router()


VEHICLE_FIELD_NAMES = (
    "vehicle_type",
    "payload_kg",
    "volume_m3",
    "has_tail_lift",
    "has_crane",
    "has_mobile_lift",
    "mobile_lift_max_floor",
    "mobile_lift_max_weight_kg",
    "crane_max_weight_kg",
    "crane_max_reach_m",
    "max_loaders",
)


def _build_vehicle_data(data: dict, loaders: int) -> dict:
    return {
        "vehicle_type": data["vehicle_type"],
        "payload_kg": data["payload_kg"],
        "volume_m3": data["volume_m3"],
        "has_tail_lift": data["has_tail_lift"],
        "has_crane": data["has_crane"],
        "has_mobile_lift": data["has_mobile_lift"],
        "mobile_lift_max_floor": data.get("mobile_lift_max_floor"),
        "mobile_lift_max_weight_kg": data.get("mobile_lift_max_weight_kg"),
        "crane_max_weight_kg": data.get("crane_max_weight_kg"),
        "crane_max_reach_m": data.get("crane_max_reach_m"),
        "max_loaders": loaders,
    }


@router.message(CarrierOnboardingStates.max_loaders)
async def max_loaders(
    message: Message,
    state: FSMContext,
) -> None:

    try:
        loaders = parse_first_int(message.text)
    except Exception:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    if loaders <= 0:
        await message.answer(text(await get_carrier_locale(state), "number_invalid"))
        return

    data = await state.get_data()
    locale = await get_carrier_locale(state)

    vehicle_count = int(data.get("vehicle_count") or 1)
    current_index = int(data.get("current_vehicle_index") or 1)
    vehicles = list(data.get("vehicles") or [])
    vehicles.append(_build_vehicle_data(data, loaders))

    if current_index < vehicle_count:
        next_index = current_index + 1

        reset_data = {name: None for name in VEHICLE_FIELD_NAMES}
        reset_data.update(
            vehicles=vehicles,
            current_vehicle_index=next_index,
        )

        await state.update_data(**reset_data)
        await state.set_state(CarrierOnboardingStates.vehicle_type)

        await message.answer(
            text(locale, "vehicle_saved", current=current_index, next=next_index, total=vehicle_count),
            reply_markup=vehicle_type_keyboard(locale),
        )
        return

    await state.update_data(
        vehicles=vehicles,
        max_loaders=loaders,
    )

    await state.set_state(CarrierOnboardingStates.company_phone)

    await message.answer(
        text(locale, "phone_prompt")
    )
