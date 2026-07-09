import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_offer_response import _delete_message_by_id_safely
from app.bot.handlers.job_offer_response import _finalize_offer_message
from app.bot.handlers.job_offer_response import router
from app.bot.offer_keyboard import build_offer_keyboard

assert router is not None
assert _finalize_offer_message is not None
assert _delete_message_by_id_safely is not None

keyboard = build_offer_keyboard(123)
assert keyboard.inline_keyboard[0][0].callback_data == "offer:accept:123"
assert keyboard.inline_keyboard[0][1].callback_data == "offer:decline:123"

source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")
assert "edit_text(text, parse_mode=\"HTML\", reply_markup=reply_markup)" in source
assert "edit_caption(caption=text, parse_mode=\"HTML\", reply_markup=reply_markup)" in source
assert "edit_reply_markup(reply_markup=reply_markup)" in source
assert "build_client_reopen_assignment_keyboard(job_id)" in source
assert "_delete_message_by_id_safely" in source
assert "sibling_offer_message_refs" in source
assert "bot.delete_message" in source

print("JOB_OFFER_RESPONSE_HANDLER_SMOKE_OK")

handler_source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")
assert "accept_offer_without_assignment" in handler_source
assert "accept_offer_and_assign_job" not in handler_source
assert "build_client_reopen_assignment_keyboard" in handler_source
assert "build_client_notification_text" not in handler_source
assert "build_carrier_notification_text" not in handler_source
assert "Ваш отклик отправлен" in handler_source

assert "accept_offer_without_assignment" in source
assert "accept_offer_and_assign_job" not in source
assert "Ваш отклик отправлен" in source

assert "OFFER_PRICE_INPUT_PREFIX" in source
assert "_parse_offer_price_input" in source
assert "update_offer_price_and_note" in source
assert "@router.message(F.reply_to_message.text.startswith(OFFER_PRICE_INPUT_PREFIX))" in source

assert "await message.edit_reply_markup(reply_markup=None)" in handler_source
assert "build_offer_decline_reason_keyboard" in handler_source
assert "offer_decline_reason:" in handler_source
assert "decline_reason=decline_reason" in handler_source
