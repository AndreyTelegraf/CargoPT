import os
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///data/cargopt_dev.db"
)

from app.bot.handlers.dispatcher_jobs_admin import (
    _build_utm_link,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    _format_leads_summary,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    _parse_leads_period,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    _parse_leads_period_args,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    dispatcher_leads,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    dispatcher_leads_campaign,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    dispatcher_leads_missing,
)
from app.bot.handlers.dispatcher_jobs_admin import (
    dispatcher_utm_link,
)


fixed_now = datetime(
    2026,
    7,
    31,
    12,
    0,
    0,
    tzinfo=UTC,
)

assert _parse_leads_period(
    "/leads",
    now=fixed_now,
) == (
    "последние 7 дней",
    "2026-07-24 12:00:00",
    "2026-07-31 12:00:00",
)

assert _parse_leads_period(
    "/leads 30d",
    now=fixed_now,
) == (
    "последние 30 дней",
    "2026-07-01 12:00:00",
    "2026-07-31 12:00:00",
)

assert _parse_leads_period_args(
    ["2026-07-01", "2026-07-31"],
    now=fixed_now,
) == (
    "с 2026-07-01 по 2026-07-31",
    "2026-07-01 00:00:00",
    "2026-07-31 23:59:59",
)

try:
    _parse_leads_period(
        "/leads 0d",
        now=fixed_now,
    )
except ValueError:
    pass
else:
    raise AssertionError("0d must be rejected")

try:
    _parse_leads_period(
        "/leads 2026-08-01",
        now=fixed_now,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "future start must be rejected"
    )

summary = _format_leads_summary(
    {
        "records": 12,
        "drafts": 2,
        "submitted": 10,
        "has_offers": 8,
        "accepted_now": 5,
        "assignment_signal": 4,
        "completed_signal": 1,
        "cancelled_now": 2,
    }
)

assert "Веб-записи: 12" in summary
assert "Отправленные заявки: 10" in summary
assert "Получили офферы: 8 (80.0%)" in summary
assert "Есть accepted-оффер сейчас: 5 (50.0%)" in summary
assert "Было назначение: 4 (40.0%)" in summary
assert "Завершены: 1 (10.0%)" in summary

assert _build_utm_link(
    locale="ru",
    source="telegram",
    medium="social",
    campaign="july_launch",
    content="post_01",
) == (
    "https://cargopt.pt/ru/"
    "?utm_source=telegram"
    "&utm_medium=social"
    "&utm_campaign=july_launch"
    "&utm_content=post_01"
)

assert _build_utm_link(
    locale="pt",
    source="reddit",
    medium="social",
    campaign="fiz_isto",
) == (
    "https://cargopt.pt/"
    "?utm_source=reddit"
    "&utm_medium=social"
    "&utm_campaign=fiz_isto"
)

try:
    _build_utm_link(
        locale="de",
        source="telegram",
        medium="social",
        campaign="test",
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "unsupported locale must be rejected"
    )

assert dispatcher_leads is not None
assert dispatcher_leads_campaign is not None
assert dispatcher_leads_missing is not None
assert dispatcher_utm_link is not None

source = Path(
    "app/bot/handlers/dispatcher_jobs_admin.py"
).read_text(encoding="utf-8")

assert 'Command("leads")' in source
assert 'Command("leads_campaign")' in source
assert 'Command("leads_missing")' in source
assert 'Command("utm_link")' in source
assert "j.source = 'web_form'" in source
assert "ACQUISITION_INTERNAL_TRAFFIC_SQL" in source
assert "utm_content" in source
assert "LIMIT 50" in source
assert (
    source.count(
        "not in CARGOPT_OPERATOR_TELEGRAM_USER_IDS"
    )
    == 10
)

print("DISPATCHER_LEADS_ADMIN_SMOKE_OK")
