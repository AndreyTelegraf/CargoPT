import importlib
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DISPATCHER_TELEGRAM_USER_IDS"] = "111, 222,111"

import app.domain.admin_access as admin_access

admin_access = importlib.reload(admin_access)

assert admin_access.ADMIN_TELEGRAM_USER_IDS == frozenset(
    {336224597}
)
assert admin_access.DISPATCHER_TELEGRAM_USER_IDS == frozenset(
    {111, 222}
)
assert admin_access.CARGOPT_OPERATOR_TELEGRAM_USER_IDS == frozenset(
    {336224597, 111, 222}
)

handler_source = Path(
    "app/bot/handlers/dispatcher_jobs_admin.py"
).read_text(encoding="utf-8")

assert (
    "from app.domain.admin_access import "
    "CARGOPT_OPERATOR_TELEGRAM_USER_IDS"
    in handler_source
)
assert "not in ADMIN_TELEGRAM_USER_IDS" not in handler_source
assert (
    handler_source.count(
        "not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS"
    )
    == 10
)

restricted_sources = (
    Path("app/bot/handlers/admin_controls.py"),
    Path("app/bot/handlers/carrier_invite_admin.py"),
    Path("app/bot/handlers/carrier_moderation_submit.py"),
)

for path in restricted_sources:
    source = path.read_text(encoding="utf-8")
    assert "ADMIN_TELEGRAM_USER_IDS" in source
    assert "CARGOPT_OPERATOR_TELEGRAM_USER_IDS" not in source

print("dispatcher_access_role_ok")
