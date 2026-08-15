from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup

from app.bot.handlers.regions import regions_keyboard
from app.bot.carrier_locale import get_carrier_locale
from app.bot.carrier_locale import text
from app.bot.states.carrier_onboarding import CarrierOnboardingStates

from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_vehicle import CarrierVehicleService

router = Router()


def submit_moderation_keyboard(locale: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=text(locale, "submit_moderation"))],
            [KeyboardButton(text=text(locale, "restart"))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _format_bool(value: bool | None, locale: str) -> str:
    return text(locale, "yes" if value else "no")


def _display(value, missing: str):
    return missing if value is None or value == "" else value


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


def _format_vehicle_preview(vehicle: dict, index: int, locale: str) -> str:
    missing = text(locale, "not_provided")
    return (
        f"{text(locale, 'vehicle', index=index)}\n"
        f"{text(locale, 'type')}: {_display(vehicle.get('vehicle_type'), missing)}\n"
        f"{text(locale, 'payload')}: {_display(vehicle.get('payload_kg'), missing)} kg\n"
        f"{text(locale, 'volume')}: {_display(vehicle.get('volume_m3'), missing)} m³\n"
        f"{text(locale, 'tail_lift')}: {_format_bool(vehicle.get('has_tail_lift'), locale)}\n"
        f"{text(locale, 'crane')}: {_format_bool(vehicle.get('has_crane'), locale)}\n"
        f"{text(locale, 'mobile_lift')}: {_format_bool(vehicle.get('has_mobile_lift'), locale)}\n"
        f"{text(locale, 'mobile_lift_floor')}: {_display(vehicle.get('mobile_lift_max_floor'), missing)}\n"
        f"{text(locale, 'mobile_lift_weight')}: {_display(vehicle.get('mobile_lift_max_weight_kg'), missing)} kg\n"
        f"{text(locale, 'crane_weight')}: {_display(vehicle.get('crane_max_weight_kg'), missing)} kg\n"
        f"{text(locale, 'crane_reach')}: {_display(vehicle.get('crane_max_reach_m'), missing)} m\n"
        f"{text(locale, 'max_loaders')}: {_display(vehicle.get('max_loaders'), missing)}"
    )


def build_carrier_preview_text(data: dict) -> str:
    locale = data.get("carrier_locale") or "ru"
    missing = text(locale, "not_provided")
    vehicles_text = "\n\n".join(
        _format_vehicle_preview(vehicle, index, locale)
        for index, vehicle in enumerate(_get_vehicles_data(data), start=1)
    )

    return (
        f"{text(locale, 'review_title')}\n\n"
        f"{text(locale, 'company')}: {data.get('company_name') or missing}\n"
        f"{text(locale, 'public_name')}: {data.get('public_name') or missing}\n"
        f"{text(locale, 'experience_since')}: {data.get('experience_since_year') or missing}\n"
        f"{text(locale, 'logo')}: {text(locale, 'uploaded' if data.get('logo_file_name') else 'not_uploaded')}\n"
        f"{text(locale, 'publication')}: {text(locale, 'publication_allowed' if data.get('publication_consent') else 'publication_unconfirmed')}\n"
        f"{text(locale, 'contact')}: {data.get('contact_name') or missing}\n\n"
        f"{text(locale, 'assembly')}: {_format_bool(data.get('assembly_required'), locale)}\n"
        f"{text(locale, 'packing')}: {_format_bool(data.get('packing_required'), locale)}\n"
        f"{text(locale, 'regions')}: {data.get('operating_regions') or missing}\n\n"
        f"{vehicles_text}\n\n"
        f"{text(locale, 'phone')}: {data.get('company_phone') or missing}\n"
        f"{text(locale, 'email')}: {data.get('company_email') or missing}\n\n"
        f"{text(locale, 'submit_hint')}"
    )


@router.message(CarrierOnboardingStates.company_email)
async def company_email(
    message: Message,
    state: FSMContext,
) -> None:

    email = (message.text or "").strip()

    if "@" not in email or "." not in email:
        await message.answer(text(await get_carrier_locale(state), "email_invalid"))
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
        reply_markup=submit_moderation_keyboard(await get_carrier_locale(state)),
    )


@router.message(
    CarrierOnboardingStates.moderation_review,
    F.text.in_([text(locale, "restart") for locale in ("pt", "en", "ru")]),
)
async def restart_carrier_onboarding(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    locale = await get_carrier_locale(state)
    if message.text != text(locale, "restart"):
        return

    carrier_id = data["carrier_id"]
    company_name = data.get("company_name") or text(locale, "not_provided")
    contact_name = data.get("contact_name")

    await state.set_data({
        "carrier_id": carrier_id,
        "company_name": company_name,
        "contact_name": contact_name,
        "public_name": data.get("public_name"),
        "experience_since_year": data.get("experience_since_year"),
        "logo_file_name": data.get("logo_file_name"),
        "publication_consent": data.get("publication_consent"),
        "carrier_locale": locale,
    })

    await state.update_data(selected_regions=[])

    await state.set_state(CarrierOnboardingStates.operating_regions)

    await message.answer(
        text(
            locale,
            "restart_intro",
            company_name=company_name,
            regions_prompt=text(locale, "regions_step_prompt"),
        ),
        reply_markup=regions_keyboard(locale=locale),
    )
