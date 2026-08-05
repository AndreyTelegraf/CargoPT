import inspect
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers import job_offer_response

source = inspect.getsource(job_offer_response.handle_offer_decline_reason)

assert "declined_offer = await offer_service.decline_offer(" in source
assert "decline_reason=decline_reason" in source
assert "has_open_offer = any(" in source
assert "OfferDistributionService(" in source
assert "send_job_offers_to_carriers(" in source
assert "escalate_job_to_manual_review" in source
assert "notify_job_control_about_unassigned_job" not in source
assert "job = None" in inspect.getsource(job_offer_response)

print("JOB_OFFER_DECLINE_EXHAUSTION_SMOKE_OK")
