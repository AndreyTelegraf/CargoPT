from aiogram import F
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.job_start import start_job_request
from app.db.session import async_session_maker
from app.domain.carrier_status import CarrierStatus
from app.repositories.carrier import CarrierRepository
from app.bot.handlers.carrier_public_profile import start_public_profile_flow
from app.services.carrier_public_profile import missing_public_profile_fields

router = Router()


def build_existing_carrier_start_text(carrier) -> str:
    if carrier.status == CarrierStatus.PENDING_MODERATION:
        return (
            "Вы уже зарегистрированы как перевозчик CargoPT.\n\n"
            "Ваша анкета отправлена на проверку.\n\n"
            "Когда она будет обработана, администратор свяжется с вами."
        )

    if carrier.status == CarrierStatus.ACTIVE:
        return (
            "Вы зарегистрированы как активный перевозчик CargoPT.\n\n"
            "Как это работает:\n"
            "- когда появится подходящий заказ, бот пришлёт вам предложение;\n"
            "- в предложении будут кнопки «Принять» и «Отказаться»;\n"
            "- после принятия заказа клиент должен подтвердить назначение.\n\n"
            "Сейчас ничего заполнять не нужно. Ожидайте новых заказов."
        )

    if carrier.status == CarrierStatus.PROFILE_COMPLETED:
        return (
            "Ваша анкета перевозчика уже заполнена.\n\n"
            "Если нужно что-то изменить, свяжитесь с администратором CargoPT."
        )

    return (
        "Вы уже привязаны к CargoPT как перевозчик.\n\n"
        "Если нужно создать клиентскую заявку на перевозку, используйте команду /new_job."
    )


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carrier = await repository.get_carrier_by_telegram_user_id(message.from_user.id)
        if carrier is not None and message.from_user.username:
            await repository.update_carrier_telegram_username(
                carrier.id,
                message.from_user.username,
            )
            await session.commit()

    if carrier is not None and carrier.status == CarrierStatus.INVITED:
        await start_public_profile_flow(
            message,
            state,
            carrier,
            update_only=False,
        )
        return

    if carrier is not None and carrier.status != CarrierStatus.REJECTED:
        if missing_public_profile_fields(carrier):
            await start_public_profile_flow(
                message,
                state,
                carrier,
                update_only=True,
            )
            return
        await state.clear()
        await message.answer(build_existing_carrier_start_text(carrier))
        return

    await start_job_request(message, state)


@router.message(F.text == "Помощь")
async def help_placeholder(message: Message) -> None:
    await message.answer(
        "Поддержка CargoPT: https://t.me/andreytelegraf"
    )
