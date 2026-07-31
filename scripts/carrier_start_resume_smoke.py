
from pathlib import Path

source = Path("app/bot/handlers/start.py").read_text()

assert "start_public_profile_flow(" in source
assert "missing_public_profile_fields(carrier)" in source
assert "carrier.status == CarrierStatus.INVITED" in source
assert "update_only=False" in source
assert "update_only=True" in source
assert "await start_job_request(message, state)" in source

print("CARRIER_START_RESUME_SMOKE_OK")
