from aiogram import F
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton
from aiogram.types import Message
from aiogram.types import ReplyKeyboardMarkup
from aiogram.types import ReplyKeyboardRemove

from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.db.session import async_session_maker
from app.domain.carrier_profile_step import CarrierProfileStep
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService

router = Router()

REGION_LABELS = {
    "Лиссабон": "Lisboa",
    "Порту": "Porto",
    "Центр": "Centro",
    "Алентежу": "Alentejo",
    "Алгарве": "Algarve",
    "Вся Португалия": "all_portugal",
}

REGION_DONE = "Готово"


def regions_keyboard(selected: list[str] | None = None) -> ReplyKeyboardMarkup:
    selected_set = set(selected or [])

    def label(title: str) -> str:
        value = REGION_LABELS[title]
        prefix = "✓ " if value in selected_set else ""
        return prefix + title

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label("Лиссабон")), KeyboardButton(text=label("Порту"))],
            [KeyboardButton(text=label("Центр")), KeyboardButton(text=label("Алентежу"))],
            [KeyboardButton(text=label("Алгарве")), KeyboardButton(text=label("Вся Португалия"))],
            [KeyboardButton(text=REGION_DONE)],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def clean_region_label(text: str) -> str:
    return text.replace("✓ ", "", 1).strip()


def format_regions(selected: list[str]) -> str:
    if "all_portugal" in selected:
        return "all_portugal"
    return ",".join(selected)


@router.message(
    CarrierOnboardingStates.operating_regions,
    F.text,
)
async def operating_regions(
    message: Message,
    state: FSMContext,
) -> None:
    raw_text = (message.text or "").strip()
    label = clean_region_label(raw_text)

    data = await state.get_data()
    selected = list(data.get("selected_regions") or [])

    if label != REGION_DONE:
        if label not in REGION_LABELS:
            await message.answer(
                "Выберите регион кнопкой или нажмите «Готово».",
                reply_markup=regions_keyboard(selected),
            )
            return

        value = REGION_LABELS[label]

        if value == "all_portugal":
            selected = ["all_portugal"]
        elif value in selected:
            selected.remove(value)
        else:
            selected = [item for item in selected if item != "all_portugal"]
            selected.append(value)

        await state.update_data(selected_regions=selected)

        await message.answer(
            "Выберите регионы работы и нажмите «Готово».",
            reply_markup=regions_keyboard(selected),
        )
        return

    if not selected:
        await message.answer(
            "Выберите хотя бы один регион работы.",
            reply_markup=regions_keyboard(selected),
        )
        return

    regions = format_regions(selected)
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        carrier = await repository.update_operating_regions(
            carrier_id,
            regions,
        )

        if data.get("profile_update_only"):
            await session.commit()
            from app.bot.handlers.carrier_public_profile import start_public_profile_flow

            await start_public_profile_flow(
                message,
                state,
                carrier,
                update_only=True,
            )
            return

        await service.advance_profile_step(
            carrier_id=carrier_id,
            step=CarrierProfileStep.VEHICLES,
        )

        await session.commit()

    await state.update_data(
        operating_regions=regions,
    )

    await state.set_state(CarrierOnboardingStates.vehicle_count)

    await message.answer(
        "Шаг 6 из 10. Автомобили.\n\n"
        "Сколько автомобилей у вашей компании?",
        reply_markup=ReplyKeyboardRemove(),
    )
