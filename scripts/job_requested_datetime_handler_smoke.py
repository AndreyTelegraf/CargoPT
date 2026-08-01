import os
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.bot.handlers.job_requested_datetime import _parse_requested_datetime
from app.bot.handlers.job_requested_datetime import router
from app.domain.requested_date import is_requested_date_in_past

assert router is not None

now = datetime(2026, 8, 1, 9, 30, tzinfo=ZoneInfo("Europe/Lisbon"))

today = _parse_requested_datetime("Сегодня", now=now)
tomorrow = _parse_requested_datetime("Завтра", now=now)
explicit_today = _parse_requested_datetime("01.08.2026 15:30", now=now)
explicit_past = _parse_requested_datetime("31.07.2026 15:30", now=now)
yearless_past = _parse_requested_datetime("31.07 10:00", now=now)

assert today == datetime(2026, 8, 1, 11, 0, tzinfo=UTC)
assert tomorrow == datetime(2026, 8, 2, 11, 0, tzinfo=UTC)
assert explicit_today == datetime(2026, 8, 1, 14, 30, tzinfo=UTC)
assert explicit_past is not None
assert yearless_past is not None
assert not is_requested_date_in_past(today, now=now)
assert not is_requested_date_in_past(explicit_today, now=now)
assert is_requested_date_in_past(explicit_past, now=now)
assert is_requested_date_in_past(yearless_past, now=now)
assert _parse_requested_datetime("не дата", now=now) is None

print("JOB_REQUESTED_DATETIME_HANDLER_SMOKE_OK")
