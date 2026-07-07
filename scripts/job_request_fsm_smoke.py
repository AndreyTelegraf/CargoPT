import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.states.job_request import JobRequestStates

assert JobRequestStates.pickup_address
assert JobRequestStates.pickup_details
assert JobRequestStates.dropoff_address
assert JobRequestStates.dropoff_details
assert JobRequestStates.item_description
assert JobRequestStates.estimated_volume_m3
assert JobRequestStates.required_loaders
assert JobRequestStates.contact_phone
assert JobRequestStates.contact_whatsapp
assert JobRequestStates.comment

print("JOB_REQUEST_FSM_SMOKE_OK")
