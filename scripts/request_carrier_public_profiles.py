import argparse
import asyncio
from datetime import UTC
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton
from aiogram.types import InlineKeyboardMarkup

from app.config import settings
from app.db.session import async_session_maker
from app.repositories.carrier import CarrierRepository


MESSAGE = (
    "Здравствуйте! Мы обновили профиль перевозчика CargoPT.\n\n"
    "Пожалуйста, дополните данные, которые будут показаны клиентам при сравнении "
    "предложений: название компании, год начала работы, логотип и регионы работы.\n\n"
    "Бот спросит только те сведения, которых пока нет в вашем профиле."
)


def keyboard(bot_username: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Дополнить профиль",
                    url=f"https://t.me/{bot_username}?start=profile",
                )
            ]
        ]
    )


async def run(*, send: bool) -> None:
    async with async_session_maker() as session:
        repository = CarrierRepository(session)
        carriers = await repository.list_public_profile_request_candidates()

        for carrier in carriers:
            username = (
                f"@{carrier.telegram_username}"
                if carrier.telegram_username
                else "username unavailable"
            )
            print(f"candidate id={carrier.id} username={username}")

        if not send:
            print(f"CARRIER_PUBLIC_PROFILE_REQUEST_DRY_RUN count={len(carriers)}")
            return

        bot = Bot(token=settings.bot_token)
        try:
            bot_identity = await bot.get_me()
            sent = 0
            failed = 0
            for carrier in carriers:
                try:
                    await bot.send_message(
                        chat_id=carrier.telegram_user_id,
                        text=MESSAGE,
                        reply_markup=keyboard(bot_identity.username),
                    )
                    requested_at = datetime.now(UTC)
                    await repository.mark_public_profile_requested(
                        carrier.id,
                        requested_at,
                    )
                    await session.commit()
                    sent += 1
                    print(f"sent carrier_id={carrier.id}")
                except Exception as exc:
                    await session.rollback()
                    failed += 1
                    print(
                        f"failed carrier_id={carrier.id} "
                        f"error={type(exc).__name__}"
                    )
            print(f"CARRIER_PUBLIC_PROFILE_REQUEST_SENT sent={sent} failed={failed}")
        finally:
            await bot.session.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(send=args.send))


if __name__ == "__main__":
    main()
