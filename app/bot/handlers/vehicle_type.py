from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text

router = Router()

ALLOWED_TYPES = {
    "Carrinha",
    "Van",
    "Camião",
    "Camião+Reboque",
}
VEHICLE_TYPE_LABELS = {
    "pt": {"Carrinha": "Carrinha", "Van": "Van", "Camião": "Camião", "Camião+Reboque": "Camião+Reboque"},
    "en": {"Small van": "Carrinha", "Van": "Van", "Truck": "Camião", "Truck + trailer": "Camião+Reboque"},
    "ru": {"Фургон": "Carrinha", "Большой фургон": "Van", "Грузовик": "Camião", "Грузовик с прицепом": "Camião+Reboque"},
}


def vehicle_type_keyboard(locale: str = "ru") -> ReplyKeyboardMarkup:
    labels = list(VEHICLE_TYPE_LABELS[locale])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0]), KeyboardButton(text=labels[1])],
            [KeyboardButton(text=labels[2]), KeyboardButton(text=labels[3])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(CarrierOnboardingStates.vehicle_type, F.text)
async def vehicle_type(
    message: Message,
    state: FSMContext,
) -> None:
    locale = await get_carrier_locale(state)
    vehicle_type_value = VEHICLE_TYPE_LABELS[locale].get(message.text or "")
    if vehicle_type_value is None:
        await message.answer(
            text(locale, "vehicle_type_invalid"),
            reply_markup=vehicle_type_keyboard(locale),
        )
        return

    data = await state.get_data()
    current_index = data.get("current_vehicle_index", 1)
    total_count = data.get("vehicle_count", 1)

    await state.update_data(
        vehicle_type=vehicle_type_value
    )

    await state.set_state(CarrierOnboardingStates.payload_kg)

    await message.answer(
        text(locale, "payload_prompt", index=current_index, total=total_count),
        reply_markup=ReplyKeyboardRemove(),
    )
