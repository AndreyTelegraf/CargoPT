import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_offer_response import build_client_assignment_confirmation_text
from app.services.assignment_notifications import send_assignment_confirmation_requests

fallback_text = build_client_assignment_confirmation_text(456)
assert "Предложение по заявке №456 выбрано." in fallback_text
assert "Свяжитесь с перевозчиком и согласуйте детали перевозки." in fallback_text
assert "Не договорились с перевозчиком" not in fallback_text

carrier = SimpleNamespace(
    telegram_user_id=7001,
    telegram_username="carrier_test",
    company_name="Test Carrier",
    contact_name="Test Contact",
    phone="+351900000000",
)

full_text = build_client_assignment_confirmation_text(456, carrier)
assert "Предложение по заявке №456 выбрано." in full_text
assert "Test Carrier" in full_text
assert "Test Contact" in full_text
assert "@carrier_test" in full_text
assert "+351900000000" in full_text
assert "Не договорились с перевозчиком" in full_text

handler_source = Path(
    "app/bot/handlers/job_offer_response.py"
).read_text(encoding="utf-8")
notification_source = Path(
    "app/services/assignment_notifications.py"
).read_text(encoding="utf-8")

client_handler = handler_source[
    handler_source.index("async def handle_client_offer_selection"):
]
notification_helper = notification_source[
    notification_source.index("async def send_assignment_confirmation_requests("):
    notification_source.index("async def send_assignment_final_notifications(")
]

assert send_assignment_confirmation_requests is not None
assert "client_telegram_user_id" not in notification_helper
assert "client_telegram_user_id=" not in client_handler
assert "callback.message.edit_text(" in client_handler
assert "reply_markup=build_client_reopen_assignment_keyboard(job_id)" in client_handler
assert "send_assignment_confirmation_requests(" in client_handler

print("CLIENT_OFFER_REUSE_ASSIGNMENT_MESSAGE_SMOKE_OK")
