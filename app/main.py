import asyncio
from contextlib import suppress

from app.bot.dispatcher import build_dispatcher
from app.scheduler.assignment_timeout import run_assignment_timeout_loop
from app.scheduler.offer_expiry import run_offer_expiry_loop
from app.scheduler.subscription_reminder import run_subscription_reminder_loop


async def run() -> None:
    bot, dp = build_dispatcher()
    offer_expiry_task = asyncio.create_task(
        run_offer_expiry_loop(bot=bot)
    )
    subscription_reminder_task = asyncio.create_task(
        run_subscription_reminder_loop(bot=bot)
    )
    assignment_timeout_task = asyncio.create_task(
        run_assignment_timeout_loop(bot=bot)
    )

    tasks = (
        offer_expiry_task,
        subscription_reminder_task,
        assignment_timeout_task,
    )

    try:
        await dp.start_polling(bot)
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
