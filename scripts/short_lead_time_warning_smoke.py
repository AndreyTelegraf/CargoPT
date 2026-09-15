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
from app.bot.handlers.job_comment import _submission_status_text


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

assert "procura automática" in short_lead_time_warning_text("pt")
assert "availability and offers are not guaranteed" in short_lead_time_warning_text("en")
assert "автоматический поиск" in short_lead_time_warning_text("ru")
assert "не гарантируются" in short_lead_time_warning_text("ru")
assert "Pedido recebido" in _submission_status_text(
    "pt-PT", queued_count=2, sent_count=0
)
assert "Request received" in _submission_status_text(
    "en-US", queued_count=2, sent_count=0
)
assert "Заявка принята" in _submission_status_text(
    "ru-RU", queued_count=2, sent_count=0
)

schema_source = (PROJECT_ROOT / "app/api/web_request_schemas.py").read_text()
api_source = (PROJECT_ROOT / "app/api/web_requests.py").read_text()
workspace_source = (
    PROJECT_ROOT / "app/static/assets/js/tracking-workspace.js"
).read_text()
track_source = (PROJECT_ROOT / "app/static/assets/js/track.js").read_text()
css_source = (PROJECT_ROOT / "app/static/assets/css/track.css").read_text()
bot_source = (PROJECT_ROOT / "app/bot/handlers/job_comment.py").read_text()
landing_source = (
    PROJECT_ROOT / "app/static/assets/js/landing.js"
).read_text()
track_pages = [
    (PROJECT_ROOT / "app/static/track/index.html").read_text(),
    (PROJECT_ROOT / "app/static/en/track/index.html").read_text(),
    (PROJECT_ROOT / "app/static/ru/track/index.html").read_text(),
]

assert "short_lead_time_warning: bool = False" in schema_source
assert "short_lead_time_warning=bool(job.short_lead_time_filtered)" in api_source
assert "tracking_snapshot?.short_lead_time_warning" in workspace_source
assert track_source.count("shortLeadTimeWarning:") == 3
assert ".tracking-short-lead-warning" in css_source
assert "message.from_user.language_code" in bot_source
assert "has_short_lead_time(result.job.requested_date)" in bot_source
assert landing_source.count("leadTimeUrgent:") == 3
assert "will not send it automatically" not in landing_source
assert "не будет автоматически рассылать" not in landing_source
assert all(
    "/assets/css/track.css?v=request-management-v1" in page
    for page in track_pages
)
assert all(
    "/assets/js/tracking-workspace.js?v=offer-terms-v1" in page
    and "/assets/js/track.js?v=offer-terms-v1" in page
    for page in track_pages
)

print("SHORT_LEAD_TIME_WARNING_SMOKE_OK")
