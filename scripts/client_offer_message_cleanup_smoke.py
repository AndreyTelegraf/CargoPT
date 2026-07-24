import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")
client_handler = source[source.index("async def handle_client_offer_selection"):]

assert (
    "build_client_assignment_confirmation_text(job_id, selected_carrier)"
    in client_handler
)
assert (
    "reply_markup=build_client_reopen_assignment_keyboard(job_id)"
    in client_handler
)
assert "Предложение выбрано. Заявка №{job_id} отправлена на подтверждение сделки." not in client_handler

print("CLIENT_OFFER_MESSAGE_CLEANUP_SMOKE_OK")
