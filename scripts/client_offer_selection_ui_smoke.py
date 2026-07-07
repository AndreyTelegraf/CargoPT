import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_offer_response import build_client_offer_selection_text
from app.bot.handlers.job_offer_response import handle_client_offer_selection
from app.bot.handlers.job_offer_response import send_client_offer_selection_message
from app.bot.offer_keyboard import build_client_offer_selection_keyboard
from app.bot.offer_keyboard import parse_client_offer_selection_callback


class View:
    offer_id = 123
    job_id = 456
    company_name = "Carrier <One>"
    vehicle_type = "large_van"
    payload_kg = 1200
    volume_m3 = 14.0
    max_loaders = 2
    price_cents = 12345
    carrier_note = "Careful <move>"


job_id, offer_id = parse_client_offer_selection_callback("client_offer:select:456:123")
assert job_id == 456
assert offer_id == 123

keyboard = build_client_offer_selection_keyboard([View()])
assert keyboard.inline_keyboard[0][0].callback_data == "client_offer:select:456:123"
assert keyboard.inline_keyboard[0][0].text == "Выбрать предложение 1"

text = build_client_offer_selection_text(456, [View()])
assert "Перевозчики откликнулись на заявку №456" in text
assert "Carrier &lt;One&gt;" in text
assert "Careful &lt;move&gt;" in text
assert "123.45 €" in text

assert handle_client_offer_selection is not None
assert send_client_offer_selection_message is not None

source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")
assert "select_accepted_offer_for_client" in source
assert "build_client_reopen_assignment_keyboard" in source
assert "ClientOfferPresentationService" in source
assert "client_offer:select" in Path("app/bot/offer_keyboard.py").read_text(encoding="utf-8")

print("CLIENT_OFFER_SELECTION_UI_SMOKE_OK")
