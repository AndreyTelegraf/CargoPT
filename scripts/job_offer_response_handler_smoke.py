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
from app.bot.offer_locale import offer_text

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
assert 't(locale, "response_sent")' in handler_source

assert "accept_offer_without_assignment" in source
assert "accept_offer_and_assign_job" not in source
assert "Your offer was sent" in offer_text("en", "response_sent")
assert "proposta foi enviada" in offer_text("pt", "response_sent")
assert "Ваш отклик отправлен" in offer_text("ru", "response_sent")

assert "_parse_offer_price_input" in source
assert "update_offer_terms" in source
assert "OfferResponseStates.price" in source
assert "OfferResponseStates.included_services" in source
assert "OfferResponseStates.possible_surcharges" in source
assert "OfferResponseStates.service_window" in source
assert "OfferResponseStates.estimate_status" in source
assert "offer_price_offer_id" in source
assert "offer_price_offer_id=offer_id" in source
assert "offer_price_message_chat_id=callback.message.chat.id" in source
assert "offer_price_message_id=callback.message.message_id" in source
assert "await state.set_state(OfferResponseStates.price)" in source
assert "await message.bot.edit_message_reply_markup(" in source
assert "chat_id=offer_message_chat_id" in source
assert "message_id=offer_message_id" in source
assert "reply_markup=None" in source
assert "await state.clear()" in source
assert "list_pending_offers_by_carrier" not in source
assert "handle_offer_terms_shortcut" in source
assert "build_offer_included_services_keyboard" in source
assert "build_offer_surcharges_keyboard" in source
assert "build_offer_service_window_keyboard" in source
assert "build_offer_estimate_status_keyboard" in source
assert "_parse_offer_price_only" in source
assert "_build_conversational_offer" in source
assert "offer_terms:" in source

assert "await message.edit_reply_markup(reply_markup=None)" in handler_source
assert "build_offer_decline_reason_keyboard" in handler_source
assert "offer_decline_reason:" in handler_source
assert "decline_reason=decline_reason" in handler_source
