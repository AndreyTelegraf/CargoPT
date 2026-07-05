import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.location_normalization import build_geocoding_queries

queries = build_geocoding_queries(
    "Praceta Manuel Faria 4, Monte Abraão, 2745-014 Queluz"
)

assert queries == [
    "Praceta Manuel Faria 4, Monte Abraão, 2745-014 Queluz",
    "2745-014 Portugal",
    "2745-014 Queluz, Portugal",
]

print("JOB_LOCATION_NOMINATIM_FALLBACK_SMOKE_OK")
