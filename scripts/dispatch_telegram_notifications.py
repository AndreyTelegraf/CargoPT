import asyncio

from aiogram import Bot

from app.config import settings
from app.reliability_logging import configure_reliability_logging
from app.db.session import async_session_maker
from app.services.telegram_dispatcher import TelegramNotificationDispatcher


async def run() -> None:
    configure_reliability_logging()
    bot = Bot(token=settings.bot_token)
    try:
        dispatcher = TelegramNotificationDispatcher(
            session_maker=async_session_maker,
            bot=bot,
            max_attempts=settings.telegram_notification_max_attempts,
            retry_base_seconds=settings.telegram_notification_retry_base_seconds,
            stale_sending_seconds=(
                settings.telegram_notification_stale_sending_seconds
            ),
        )
        processed = await dispatcher.dispatch_due(
            limit=settings.telegram_notification_dispatch_limit
        )
        print(f"TELEGRAM_DISPATCH_PROCESSED={processed}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
