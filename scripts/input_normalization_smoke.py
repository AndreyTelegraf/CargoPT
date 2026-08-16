import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.input_normalization import parse_first_float
from app.services.input_normalization import parse_first_int

assert parse_first_int("1600 кг") == 1600
assert parse_first_int("до 3500 кг") == 3500
assert parse_first_int("2 грузчика") == 2
assert parse_first_int("этаж 12") == 12
assert parse_first_int("до 500kg") == 500

assert parse_first_float("18 м3") == 18.0
assert parse_first_float("18,5 м³") == 18.5
assert parse_first_float("объем 12.7") == 12.7
assert parse_first_float("0.25 м³") == 0.25
assert parse_first_float("0,25 м³") == 0.25
assert parse_first_float("0.0001 м³") == 0.0001

for bad in ["", "кг", "примерно"]:
    try:
        parse_first_int(bad)
    except ValueError:
        pass
    else:
        raise SystemExit(f"expected parse_first_int failure for {bad!r}")

print("INPUT_NORMALIZATION_SMOKE_OK")
