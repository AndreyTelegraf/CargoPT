from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from app.bot.handlers.regions import regions_keyboard
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.domain.carrier_profile_step import CarrierProfileStep
from app.bot.states.carrier_onboarding import CarrierOnboardingStates

router = Router()


def carrier_welcome_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Начать")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def carrier_yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


@router.message(CommandStart(deep_link=True))
async def invite_start(message: Message, state: FSMContext) -> None:
    payload = (message.text or "").split(maxsplit=1)

    if len(payload) != 2:
        await message.answer(
            "У вас нет приглашения. Обратитесь к администратору CargoPT."
        )
        return

    token = payload[1].strip()

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        existing_carrier = await repository.get_carrier_by_telegram_user_id(
            message.from_user.id
        )
        if existing_carrier is not None:
            await session.commit()
            await state.clear()
            await message.answer(
                "Вы уже зарегистрированы как перевозчик CargoPT. "
                "Если нужно изменить анкету или пройти её заново, свяжитесь с администратором."
            )
            return

        try:
            invite = await service.claim_invite_token(
                token=token,
                telegram_user_id=message.from_user.id,
                telegram_username=message.from_user.username,
            )

            carrier = await repository.get_carrier_by_id(invite.carrier_id)

            if carrier is None:
                raise ValueError("carrier not found")

            await session.commit()

        except Exception:
            await session.rollback()
            await message.answer(
                "Приглашение недействительно или уже использовано."
            )
            return

    await state.update_data(
        carrier_id=invite.carrier_id,
        company_name=carrier.company_name,
        contact_name=carrier.contact_name,
    )

    await state.set_state(
        CarrierOnboardingStates.welcome
    )

    await message.answer(
        "Добро пожаловать в CargoPT.\n\n"
        "Вы были приглашены как перевозчик.\n\n"
        f"Компания:\n{carrier.company_name}\n\n"
        "Сейчас нужно заполнить анкету перевозчика.\n\n"
        "Что потребуется:\n"
        "- регионы работы\n"
        "- автомобили и их характеристики\n"
        "- услуги сборки и упаковки\n"
        "- контактные данные\n\n"
        "Анкета состоит из 6 шагов и обычно занимает 2–3 минуты.\n\n"
        "Нажмите «Начать».",
        reply_markup=carrier_welcome_keyboard(),
    )


@router.message(CarrierOnboardingStates.welcome, lambda message: message.text == "Начать")
async def carrier_welcome_start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        await service.advance_profile_step(
            carrier_id=carrier_id,
            step=CarrierProfileStep.OPERATING_REGIONS,
        )

        await session.commit()

    await state.update_data(selected_regions=[])

    await state.set_state(CarrierOnboardingStates.operating_regions)

    await message.answer(
        "Шаг 1 из 6. Регионы работы.\n\n"
        "В каких регионах Португалии вы работаете?\n\n"
        "Можно выбрать несколько регионов. Когда закончите, нажмите «Готово».",
        reply_markup=regions_keyboard(),
    )
