import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.location_normalization import extract_google_continue_url
from app.services.location_normalization import extract_google_maps_query_address

url = "https://consent.google.com/ml?continue=https://maps.google.com/maps?q%3DR.%2BAlexandre%2BBraga%2B14,%2B1000-236%2BLisboa%26entry%3Dgps"
continue_url = extract_google_continue_url(url)
assert continue_url == "https://maps.google.com/maps?q=R.+Alexandre+Braga+14,+1000-236+Lisboa&entry=gps"

address = extract_google_maps_query_address(continue_url)
assert address == "R. Alexandre Braga 14, 1000-236 Lisboa"

print("JOB_LOCATION_GOOGLE_CONSENT_SMOKE_OK")
