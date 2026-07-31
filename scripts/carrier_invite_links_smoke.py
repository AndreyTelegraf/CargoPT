import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.carrier_invite_admin import carrier_invite
from app.bot.handlers.carrier_invite_admin import router
from app.bot.handlers.invite import invite_start

assert router is not None
assert carrier_invite is not None
assert invite_start is not None

invite_source = Path("app/bot/handlers/invite.py").read_text(encoding="utf-8")
welcome_handler_source = invite_source[
    invite_source.index("async def carrier_welcome_start"):
]
assert "await start_public_profile_flow(" in welcome_handler_source
assert "update_only=False" in welcome_handler_source
assert 'token == "profile"' in invite_source

router_source = Path("app/bot/routers.py").read_text(encoding="utf-8")
assert "carrier_invite_admin_router" in router_source

admin_source = Path("app/bot/handlers/carrier_invite_admin.py").read_text(encoding="utf-8")
assert "Command(\"carrier_invite\")" in admin_source
assert "https://t.me/" in admin_source
assert "create_draft_carrier" in admin_source
assert "create_invite_token" in admin_source

print("CARRIER_INVITE_LINKS_SMOKE_OK")
