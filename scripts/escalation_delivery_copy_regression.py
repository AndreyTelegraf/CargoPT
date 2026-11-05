import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
from app.services.job_escalation import build_offer_escalation_text
from app.services.job_matching import MatchingReason

job = SimpleNamespace(id=1, status="manual_review_required")
text = build_offer_escalation_text(job=job, offers=[], matching_reason=MatchingReason.REQUESTED_DATE_PASSED)
assert "Автоматическая рассылка не запускалась." in text
assert "Желаемая дата перевозки прошла." in text
text = build_offer_escalation_text(job=job, offers=[SimpleNamespace(status="expired")])
assert "Создано предложений: 1." in text
assert "получили заявку" not in text
print("ESCALATION_DELIVERY_COPY_REGRESSION_OK")
