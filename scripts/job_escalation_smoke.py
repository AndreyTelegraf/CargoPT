import os
import sys
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.job_escalation import build_offer_escalation_text
from app.services.job_escalation import escalate_job_to_manual_review
from app.services.job_escalation import notify_admins_about_unassigned_job

assert escalate_job_to_manual_review is not None
assert notify_admins_about_unassigned_job is not None

job = SimpleNamespace(
    id=43,
    status="offered",
    client_telegram_username="AnnaRyaskina",
    client_telegram_user_id=500965606,
)
offers = [
    SimpleNamespace(status="declined"),
    SimpleNamespace(status="expired"),
    SimpleNamespace(status="pending"),
]

text = build_offer_escalation_text(job=job, offers=offers)

assert "Заявка #43" in text
assert "Клиент: @AnnaRyaskina" in text
assert "Причина:" in text
assert "Не удалось найти перевозчика." in text
assert "Рассылка завершена." in text
assert "3 перевозчиков получили заявку." in text
assert "1 отказались." in text
assert "1 не ответили." in text
assert "1 ожидают ответа." in text
assert "Принятых предложений нет." in text
assert "Рекомендуем:" in text
assert "добавить новых перевозчиков" in text
assert "отправить вручную" in text
assert "связаться с клиентом" in text

source = Path("app/services/job_escalation.py").read_text(encoding="utf-8")
assert "JobStatus.MANUAL_REVIEW_REQUIRED" in source
assert "list_offers_by_job(job.id)" in source
assert "notify_admins_about_unassigned_job" in source

request_submission_source = Path("app/services/request_submission.py").read_text(encoding="utf-8")
expiry_source = Path("app/services/offer_expiry.py").read_text(encoding="utf-8")
handler_source = Path("app/bot/handlers/job_offer_response.py").read_text(encoding="utf-8")

assert "escalate_job_to_manual_review" in request_submission_source
assert "if not offers:" in request_submission_source
assert "escalate_job_to_manual_review" in expiry_source
assert "escalate_job_to_manual_review" in handler_source
assert "notify_admins_about_unassigned_job(" not in request_submission_source
assert "notify_admins_about_unassigned_job(" not in expiry_source
assert "notify_admins_about_unassigned_job(" not in handler_source

print("JOB_ESCALATION_SMOKE_OK")
