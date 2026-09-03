import asyncio
import os
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.domain.job_status import JobStatus
from app.services.job_escalation import build_offer_escalation_text
from app.services.job_matching import MatchingReason
from app.services.request_submission import RequestSubmissionService
from app.services.short_lead_time_warning import should_filter_short_lead_time


class FakeJobRepository:
    def __init__(self, requested_date):
        now = datetime.now(UTC)
        self.job = SimpleNamespace(
            id=901,
            status=JobStatus.DRAFT,
            requested_date=requested_date,
            short_lead_time_filtered=False,
            client_telegram_username="short_lead_client",
            client_telegram_user_id=123,
            updated_at=now,
        )

    async def count_active_client_jobs(self, telegram_user_id):
        return 0

    async def count_sent_client_jobs_since(self, telegram_user_id, since):
        return 0

    async def update_comment_and_status(self, *, job_id, comment, status, updated_at):
        self.job.status = status
        self.job.updated_at = updated_at
        return self.job

    async def list_offers_by_job(self, job_id):
        return []

    async def update_job_status(self, *, job_id, status, updated_at):
        self.job.status = status
        self.job.updated_at = updated_at
        return self.job


class FailIfUsedCarrierRepository:
    def __getattr__(self, name):
        raise AssertionError(f"carrier matching must not run: {name}")


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))


async def exercise_submission_filter() -> None:
    repository = FakeJobRepository(datetime.now(UTC) + timedelta(hours=1))
    bot = FakeBot()
    service = RequestSubmissionService(
        job_repository=repository,
        carrier_repository=FailIfUsedCarrierRepository(),
        bot=bot,
    )

    result = await service.submit_existing_job(
        job_id=repository.job.id,
        comment=None,
        client_telegram_user_id=repository.job.client_telegram_user_id,
        enforce_telegram_client_limits=True,
    )

    assert result.offers_count == 0
    assert result.sent_count == 0
    assert result.job.status == JobStatus.MANUAL_REVIEW_REQUIRED
    assert result.job.short_lead_time_filtered is True
    assert bot.messages
    assert "меньше 72 часов" in bot.messages[0][1]["text"]
    assert "не запускалась" in bot.messages[0][1]["text"]


def assert_boundaries_and_wiring() -> None:
    now = datetime(2026, 9, 3, 12, 0, tzinfo=UTC)
    assert should_filter_short_lead_time(now - timedelta(seconds=1), now=now)
    assert should_filter_short_lead_time(now + timedelta(hours=71, minutes=59), now=now)
    assert not should_filter_short_lead_time(now + timedelta(hours=72), now=now)
    assert not should_filter_short_lead_time(None, now=now)

    expected_callers = (
        "app/services/request_submission.py",
        "app/services/offer_expiry.py",
        "app/bot/handlers/job_offer_response.py",
        "app/services/assignment_confirmation.py",
    )
    for relative_path in expected_callers:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "hold_short_lead_job_for_manual_review" in source, relative_path

    carrier_approval = (
        PROJECT_ROOT / "app/bot/handlers/carrier_moderation_submit.py"
    ).read_text(encoding="utf-8")
    assert "Job.requested_date >= now + timedelta(hours=72)" in carrier_approval

    model_source = (PROJECT_ROOT / "app/models/job.py").read_text(encoding="utf-8")
    migration_source = (
        PROJECT_ROOT
        / "migrations/versions/20260903_1200_filter_short_lead_requests.py"
    ).read_text(encoding="utf-8")
    assert "short_lead_time_filtered" in model_source
    assert "short_lead_time_filtered" in migration_source

    web_job = SimpleNamespace(
        id=902,
        status=JobStatus.MANUAL_REVIEW_REQUIRED,
        client_telegram_username=None,
        client_telegram_user_id=None,
        customer_name="Cliente Web",
        customer_email="cliente@example.com",
        client_phone=None,
        client_whatsapp=None,
    )
    escalation_text = build_offer_escalation_text(
        job=web_job,
        offers=[],
        matching_reason=MatchingReason.SHORT_LEAD_TIME,
    )
    assert "Клиент: Cliente Web" in escalation_text
    assert "@None" not in escalation_text
    assert "переноса" in escalation_text


async def main() -> None:
    assert_boundaries_and_wiring()
    await exercise_submission_filter()
    print("SHORT_LEAD_FILTER_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
