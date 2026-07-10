import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.admin_controls import ban_client
from app.bot.handlers.admin_controls import router
from app.bot.handlers.admin_controls import unban_client

assert router is not None
assert ban_client is not None
assert unban_client is not None

router_source = Path("app/bot/routers.py").read_text(encoding="utf-8")
job_start_source = Path("app/bot/handlers/job_start.py").read_text(encoding="utf-8")
request_draft_source = Path("app/services/request_draft.py").read_text(
    encoding="utf-8"
)
admin_source = Path("app/bot/handlers/admin_controls.py").read_text(encoding="utf-8")

assert "admin_controls_router" in router_source
assert "dp.include_router(admin_controls_router)" in router_source
assert "RequestDraftService" in job_start_source
assert "ClientBannedError" in job_start_source
assert "временно отключены" in job_start_source
assert "get_active_client_ban" in request_draft_source
assert 'raise ClientBannedError("client_banned")' in request_draft_source
assert "Command(\"ban\")" in admin_source
assert "Command(\"unban\")" in admin_source
assert "ADMIN_TELEGRAM_USER_IDS" in admin_source
assert "app.db.session import async_session_maker" in admin_source

print("ADMIN_CLIENT_BAN_COMMANDS_SMOKE_OK")
