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
from app.db.session import async_session_maker
from app.domain.carrier_profile_step import CarrierProfileStep
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService

router = Router()

REGION_LABELS = {
    "pt": {"Lisboa": "Lisboa", "Porto": "Porto", "Centro": "Centro", "Alentejo": "Alentejo", "Algarve": "Algarve", "Todo o Portugal": "all_portugal"},
    "en": {"Lisbon": "Lisboa", "Porto": "Porto", "Central Portugal": "Centro", "Alentejo": "Alentejo", "Algarve": "Algarve", "All Portugal": "all_portugal"},
    "ru": {"Лиссабон": "Lisboa", "Порту": "Porto", "Центр": "Centro", "Алентежу": "Alentejo", "Алгарве": "Algarve", "Вся Португалия": "all_portugal"},
}


def regions_keyboard(selected: list[str] | None = None, locale: str = "ru") -> ReplyKeyboardMarkup:
    selected_set = set(selected or [])
    labels = REGION_LABELS[locale]

    def label(title: str) -> str:
        value = labels[title]
        prefix = "✓ " if value in selected_set else ""
        return prefix + title

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=label(list(labels)[0])), KeyboardButton(text=label(list(labels)[1]))],
            [KeyboardButton(text=label(list(labels)[2])), KeyboardButton(text=label(list(labels)[3]))],
            [KeyboardButton(text=label(list(labels)[4])), KeyboardButton(text=label(list(labels)[5]))],
            [KeyboardButton(text=text(locale, "done"))],
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
    locale = await get_carrier_locale(state)
    labels = REGION_LABELS[locale]

    data = await state.get_data()
    selected = list(data.get("selected_regions") or [])

    if label != text(locale, "done"):
        if label not in labels:
            await message.answer(
                text(locale, "regions_invalid"),
                reply_markup=regions_keyboard(selected, locale),
            )
            return

        value = labels[label]

        if value == "all_portugal":
            selected = ["all_portugal"]
        elif value in selected:
            selected.remove(value)
        else:
            selected = [item for item in selected if item != "all_portugal"]
            selected.append(value)

        await state.update_data(selected_regions=selected)

        await message.answer(
            text(locale, "regions_short_prompt"),
            reply_markup=regions_keyboard(selected, locale),
        )
        return

    if not selected:
        await message.answer(
            text(locale, "regions_required"),
            reply_markup=regions_keyboard(selected, locale),
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
        text(locale, "vehicles_count_prompt"),
        reply_markup=ReplyKeyboardRemove(),
    )
