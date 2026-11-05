import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.offer_notification import send_job_offers_to_carriers

assert send_job_offers_to_carriers is not None

from app.services.telegram_delivery_plan import build_delivery_plan

for kind in ("photo", "video"):
    plan = build_delivery_plan(dict(job_id=1, offer_id=1, notification_type="carrier_offer",
        payload={"text": "<b>text</b>"}, media=[{"media_type": kind, "telegram_file_id": "file"}]))
    assert plan[0]["method"] == f"send_{kind}"
    assert plan[0]["kwargs"]["caption"] == "<b>text</b>"
    assert plan[0]["kwargs"]["parse_mode"] == "HTML"
    assert plan[0]["kwargs"]["reply_markup"]
print("JOB_OFFER_SEND_MEDIA_HANDLER_SMOKE_OK")
