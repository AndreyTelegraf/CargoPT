import os
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.short_lead_time_warning import has_short_lead_time
from app.services.short_lead_time_warning import normalize_warning_locale
from app.services.short_lead_time_warning import short_lead_time_warning_text


now = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)

assert has_short_lead_time(now + timedelta(hours=1), now=now)
assert has_short_lead_time(now + timedelta(hours=71, minutes=59), now=now)
assert not has_short_lead_time(now + timedelta(hours=72), now=now)
assert not has_short_lead_time(now - timedelta(seconds=1), now=now)
assert not has_short_lead_time(None, now=now)

assert normalize_warning_locale("pt-PT") == "pt"
assert normalize_warning_locale("en-US") == "en"
assert normalize_warning_locale("ru_RU") == "ru"
assert normalize_warning_locale(None, default_locale="ru") == "ru"

assert "três dias" in short_lead_time_warning_text("pt")
assert "three days" in short_lead_time_warning_text("en")
assert "трёх суток" in short_lead_time_warning_text("ru")

schema_source = (PROJECT_ROOT / "app/api/web_request_schemas.py").read_text()
api_source = (PROJECT_ROOT / "app/api/web_requests.py").read_text()
workspace_source = (
    PROJECT_ROOT / "app/static/assets/js/tracking-workspace.js"
).read_text()
track_source = (PROJECT_ROOT / "app/static/assets/js/track.js").read_text()
css_source = (PROJECT_ROOT / "app/static/assets/css/track.css").read_text()
bot_source = (PROJECT_ROOT / "app/bot/handlers/job_comment.py").read_text()
track_pages = [
    (PROJECT_ROOT / "app/static/track/index.html").read_text(),
    (PROJECT_ROOT / "app/static/en/track/index.html").read_text(),
    (PROJECT_ROOT / "app/static/ru/track/index.html").read_text(),
]

assert "short_lead_time_warning: bool = False" in schema_source
assert "short_lead_time_warning=has_short_lead_time" in api_source
assert "tracking_snapshot?.short_lead_time_warning" in workspace_source
assert track_source.count("shortLeadTimeWarning:") == 3
assert ".tracking-short-lead-warning" in css_source
assert "message.from_user.language_code" in bot_source
assert all(page.count("short-lead-v1") == 3 for page in track_pages)

print("SHORT_LEAD_TIME_WARNING_SMOKE_OK")
