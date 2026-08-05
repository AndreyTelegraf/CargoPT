import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DISPATCHER_TELEGRAM_USER_IDS"] = "111,222"
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.job_completion import notify_job_control_about_completion_problem
from app.services.job_escalation import notify_job_control_about_unassigned_job


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, *, chat_id: int, text: str) -> None:
        self.messages.append((chat_id, text))


async def main() -> None:
    bot = FakeBot()
    job = SimpleNamespace(
        id=130,
        status="manual_review_required",
        client_telegram_username=None,
        client_telegram_user_id=123,
    )

    await notify_job_control_about_unassigned_job(
        bot=bot,
        job=job,
        offers=[],
    )
    await notify_job_control_about_completion_problem(
        bot=bot,
        job=job,
        actor="client",
    )

    assert len(bot.messages) == 4
    assert {chat_id for chat_id, _ in bot.messages[:2]} == {111, 222}
    assert {chat_id for chat_id, _ in bot.messages[2:]} == {111, 222}
    assert all(chat_id != 336224597 for chat_id, _ in bot.messages)
    assert "Заявка #130" in bot.messages[0][1]
    assert "отмечена проблема" in bot.messages[2][1]


asyncio.run(main())

print("JOB_CONTROL_ROUTING_SMOKE_OK")
