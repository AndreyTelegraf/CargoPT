from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.db.session import async_session_maker
from app.domain.admin_access import ADMIN_TELEGRAM_USER_IDS
from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService

router = Router()


@router.message(Command("carrier_invite"))
async def carrier_invite(message: Message) -> None:
    if message.from_user.id not in ADMIN_TELEGRAM_USER_IDS:
        await message.answer("Команда доступна только администратору CargoPT.")
        return

    raw_text = (message.text or "").strip()
    parts = raw_text.split(maxsplit=1)

    if len(parts) != 2 or not parts[1].strip():
        await message.answer(
            "Команда создаёт ссылку для анкеты перевозчика.\n\n"
            "Формат:\n"
            "/carrier_invite Название компании"
        )
        return

    company_name = parts[1].strip()

    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        existing_carrier = await repository.get_latest_carrier_by_company_name(
            company_name
        )

        if existing_carrier is None:
            carrier = await service.create_draft_carrier(
                company_name=company_name,
                contact_name=None,
                phone=None,
                internal_note=f"Invite created by Telegram user {message.from_user.id}",
            )
        else:
            carrier = await service.reuse_carrier_for_reinvite(
                carrier_id=existing_carrier.id,
            )

        invite = await service.create_invite_token(
            carrier_id=carrier.id,
            created_by_admin_id=message.from_user.id,
            expires_in_days=30,
        )

        await session.commit()

    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    if not bot_username:
        await message.answer(
            "Приглашение создано, но бот не вернул username. "
            "Проверьте BotFather username перед отправкой ссылки."
        )
        return

    invite_link = f"https://t.me/{bot_username}?start={invite.token}"

    await message.answer(
        "Ссылка для анкеты перевозчика создана.\n\n"
        f"Компания: {company_name}\n"
        f"Срок действия: 30 дней\n\n"
        f"{invite_link}"
    )
