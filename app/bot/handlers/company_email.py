from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup

from app.bot.handlers.regions import regions_keyboard
from app.bot.states.carrier_onboarding import CarrierOnboardingStates

from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_vehicle import CarrierVehicleService

router = Router()


def submit_moderation_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить на модерацию")],
            [KeyboardButton(text="Заполнить заново")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _format_bool(value: bool | None) -> str:
    return "Да" if value else "Нет"


def _get_vehicles_data(data: dict) -> list[dict]:
    vehicles = list(data.get("vehicles") or [])

    if vehicles:
        return vehicles

    return [
        {
            "vehicle_type": data.get("vehicle_type"),
            "payload_kg": data.get("payload_kg"),
            "volume_m3": data.get("volume_m3"),
            "has_tail_lift": data.get("has_tail_lift"),
            "has_crane": data.get("has_crane"),
            "has_mobile_lift": data.get("has_mobile_lift"),
            "mobile_lift_max_floor": data.get("mobile_lift_max_floor"),
            "mobile_lift_max_weight_kg": data.get("mobile_lift_max_weight_kg"),
            "crane_max_weight_kg": data.get("crane_max_weight_kg"),
            "crane_max_reach_m": data.get("crane_max_reach_m"),
            "max_loaders": data.get("max_loaders"),
        }
    ]


def _format_vehicle_preview(vehicle: dict, index: int) -> str:
    return (
        f"Автомобиль {index}\n"
        f"Тип: {vehicle.get('vehicle_type', 'не указано')}\n"
        f"Грузоподъёмность: {vehicle.get('payload_kg', 'не указано')} кг\n"
        f"Объём: {vehicle.get('volume_m3', 'не указано')} м³\n"
        f"Гидроборт: {_format_bool(vehicle.get('has_tail_lift'))}\n"
        f"Кран: {_format_bool(vehicle.get('has_crane'))}\n"
        f"Мобильный лифт: {_format_bool(vehicle.get('has_mobile_lift'))}\n"
        f"Макс. этаж мобильного лифта: {vehicle.get('mobile_lift_max_floor', 'не указано')}\n"
        f"Макс. вес мобильного лифта: {vehicle.get('mobile_lift_max_weight_kg', 'не указано')} кг\n"
        f"Макс. вес крана: {vehicle.get('crane_max_weight_kg', 'не указано')} кг\n"
        f"Вылет стрелы крана: {vehicle.get('crane_max_reach_m', 'не указано')} м\n"
        f"Макс. грузчиков для автомобиля: {vehicle.get('max_loaders', 'не указано')}"
    )


def build_carrier_preview_text(data: dict) -> str:
    vehicles_text = "\n\n".join(
        _format_vehicle_preview(vehicle, index)
        for index, vehicle in enumerate(_get_vehicles_data(data), start=1)
    )

    return (
        "Проверьте анкету перевозчика перед отправкой на модерацию.\n\n"
        f"Компания: {data.get('company_name', 'не указано')}\n"
        f"Название в карточке: {data.get('public_name', 'не указано')}\n"
        f"В перевозках с: {data.get('experience_since_year', 'не указано')} года\n"
        f"Логотип: {'загружен' if data.get('logo_file_name') else 'не загружен'}\n"
        f"Публикация: {'разрешена' if data.get('publication_consent') else 'не подтверждена'}\n"
        f"Контакт: {data.get('contact_name') or 'не указан'}\n\n"
        f"Сборка/разборка мебели: {_format_bool(data.get('assembly_required'))}\n"
        f"Упаковка груза: {_format_bool(data.get('packing_required'))}\n"
        f"Регионы работы: {data.get('operating_regions', 'не указано')}\n\n"
        f"{vehicles_text}\n\n"
        f"Телефон: {data.get('company_phone', 'не указано')}\n"
        f"Email: {data.get('company_email', 'не указано')}\n\n"
        "Если всё верно, нажмите «Отправить на модерацию»."
    )


@router.message(CarrierOnboardingStates.company_email)
async def company_email(
    message: Message,
    state: FSMContext,
) -> None:

    email = message.text.strip()

    if "@" not in email or "." not in email:
        await message.answer("Укажите корректный email компании.")
        return

    await state.update_data(
        company_email=email
    )

    data = await state.get_data()
    carrier_id = data["carrier_id"]
    vehicles_data = _get_vehicles_data(data)

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierVehicleService(repository)

        existing_vehicles = await repository.list_vehicles_by_carrier(carrier_id)

        for vehicle in existing_vehicles:
            await session.delete(vehicle)

        await session.flush()

        for vehicle in vehicles_data:
            await service.create_vehicle(
                carrier_id=carrier_id,
                vehicle_type=vehicle["vehicle_type"],
                payload_kg=vehicle["payload_kg"],
                volume_m3=vehicle["volume_m3"],
                has_tail_lift=vehicle["has_tail_lift"],
                has_crane=vehicle["has_crane"],
                has_mobile_lift=vehicle["has_mobile_lift"],
                mobile_lift_max_floor=vehicle.get("mobile_lift_max_floor"),
                mobile_lift_max_weight_kg=vehicle.get("mobile_lift_max_weight_kg"),
                crane_max_weight_kg=vehicle.get("crane_max_weight_kg"),
                crane_reach_meters=vehicle.get("crane_max_reach_m"),
                max_loaders=vehicle.get("max_loaders"),
            )

        await session.commit()

    await state.set_state(CarrierOnboardingStates.moderation_review)

    await message.answer(
        build_carrier_preview_text(data),
        reply_markup=submit_moderation_keyboard(),
    )


@router.message(
    CarrierOnboardingStates.moderation_review,
    lambda message: message.text == "Заполнить заново",
)
async def restart_carrier_onboarding(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    carrier_id = data["carrier_id"]
    company_name = data.get("company_name", "не указано")
    contact_name = data.get("contact_name")

    await state.set_data({
        "carrier_id": carrier_id,
        "company_name": company_name,
        "contact_name": contact_name,
        "public_name": data.get("public_name"),
        "experience_since_year": data.get("experience_since_year"),
        "logo_file_name": data.get("logo_file_name"),
        "publication_consent": data.get("publication_consent"),
    })

    await state.update_data(selected_regions=[])

    await state.set_state(CarrierOnboardingStates.operating_regions)

    await message.answer(
        f"Компания:\n{company_name}\n\n"
        "Заполним анкету заново.\n\n"
        "Шаг 5 из 10. Регионы работы.\n\n"
        "В каких регионах Португалии вы работаете?\n\n"
        "Можно выбрать несколько регионов. Когда закончите, нажмите «Готово».",
        reply_markup=regions_keyboard(),
    )
