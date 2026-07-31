from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup
from aiogram.fsm.context import FSMContext

from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService
from app.domain.carrier_status import CarrierStatus
from app.bot.states.carrier_onboarding import CarrierOnboardingStates
from app.bot.handlers.carrier_public_profile import start_public_profile_flow

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
        if token == "profile":
            if existing_carrier is None or existing_carrier.status == CarrierStatus.REJECTED:
                await message.answer("Профиль перевозчика не найден.")
                return
            if message.from_user.username:
                await repository.update_carrier_telegram_username(
                    existing_carrier.id,
                    message.from_user.username,
                )
            await session.commit()
            await start_public_profile_flow(
                message,
                state,
                existing_carrier,
                update_only=True,
            )
            return
        if (
            existing_carrier is not None
            and existing_carrier.status == CarrierStatus.INVITED
        ):
            await session.commit()
            await start_public_profile_flow(
                message,
                state,
                existing_carrier,
                update_only=False,
            )
            return

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
        "- название для публичной карточки\n"
        "- год начала работы и логотип\n"
        "- регионы работы\n"
        "- автомобили и их характеристики\n"
        "- услуги сборки и упаковки\n"
        "- контактные данные\n\n"
        "Анкета состоит из 10 шагов и обычно занимает 4–5 минут.\n\n"
        "Нажмите «Начать».",
        reply_markup=carrier_welcome_keyboard(),
    )


@router.message(CarrierOnboardingStates.welcome, lambda message: message.text == "Начать")
async def carrier_welcome_start(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    carrier_id = data["carrier_id"]

    async with async_session_maker() as session:
        carrier = await CarrierRepository(session).get_carrier_by_id(carrier_id)

    if carrier is None:
        await message.answer("Анкета перевозчика не найдена.")
        return

    await start_public_profile_flow(
        message,
        state,
        carrier,
        update_only=False,
    )
