import asyncio
import inspect
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/cargopt_dev.db")

from app.bot.assignment_confirmation_keyboard import build_assignment_failure_reason_keyboard
from app.bot.handlers import job_assignment_confirmation
from app.services.assignment_notifications import send_assignment_final_notifications


class Bot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


class Carriers:
    session = object()
    async def get_carrier_by_id(self, carrier_id):
        return SimpleNamespace(
            id=carrier_id,
            telegram_user_id=7001,
            preferred_locale="pt",
        )


async def main() -> None:
    reasons = build_assignment_failure_reason_keyboard(7, locale="en")
    assert reasons.inline_keyboard[0][0].text == "Time unavailable"

    bot = Bot()
    notifications = SimpleNamespace(enqueue_message=AsyncMock())
    with patch("app.services.telegram_notifications.notification_service_for", return_value=notifications):
        await send_assignment_final_notifications(
            bot=bot,
            job=SimpleNamespace(id=7, status="assigned", client_telegram_user_id=None),
            accepted_offer=SimpleNamespace(id=9, carrier_id=3),
            carrier_repository=Carriers(),
        )
    assert not bot.messages
    payload = notifications.enqueue_message.await_args.kwargs
    assert payload["text"].startswith("🟢 Estado\n")
    assert "confirmado por ambas as partes" in payload["text"]

    handler_source = inspect.getsource(
        job_assignment_confirmation.handle_assignment_confirmation
    )
    assert "locale_carrier.preferred_locale" in handler_source
    assert "build_assignment_failure_reason_keyboard(" in handler_source
    assert "locale=locale" in handler_source

    print("ASSIGNMENT_LOCALE_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
