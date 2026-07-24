import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.offer_notification import send_job_offers_to_carriers

assert send_job_offers_to_carriers is not None

source = Path("app/services/offer_notification.py").read_text(encoding="utf-8")
assert "list_media_by_job" in source
assert "send_photo" in source
assert "send_video" in source
assert "send_media_group" in source
assert "caption=offer_text" in source
assert 'parse_mode="HTML"' in source
assert "Решение по заявке" in source

print("JOB_OFFER_SEND_MEDIA_HANDLER_SMOKE_OK")
