import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_offer_response import send_assignment_confirmation_requests
from app.bot.handlers.job_offer_response import handle_client_offer_selection

assert send_assignment_confirmation_requests is not None
assert handle_client_offer_selection is not None

source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")

assert "build_client_reopen_assignment_keyboard" in source
assert "send_assignment_confirmation_requests" in source
assert "selected_offer = await offer_service.select_accepted_offer_for_client" in source
assert "selected_carrier = await carrier_repository.get_carrier_by_id" in source
assert "Клиент выбрал ваше предложение" in source
assert "подтвердите сделку" not in source.lower()

print("CLIENT_OFFER_ASSIGNMENT_DISPATCH_SMOKE_OK")
