import asyncio
import os
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.services.job_matching import MatchingReason
from app.services.offer_distribution import OfferDistributionService
from app.services.request_submission import RequestSubmissionService


class FakeJobRepository:
    def __init__(self, requested_date):
        now = datetime.now(UTC)
        self.committed = False
        self.job = SimpleNamespace(
            id=901,
            status="draft",
            requested_date=requested_date,
            short_lead_time_filtered=False,
            client_telegram_username="urgent_client",
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

    async def commit(self):
        self.committed = True


class FakeTelegramNotificationService:
    def __init__(self):
        self.carrier_notifications = []

    async def enqueue_carrier_offers(self, **kwargs):
        self.carrier_notifications.append(kwargs)
        return [SimpleNamespace(id=701)]

    async def enqueue_manual_review(self, **kwargs):
        raise AssertionError("urgent lead time must not notify job control")


async def exercise_urgent_submission_distribution() -> None:
    repository = FakeJobRepository(datetime.now(UTC) + timedelta(hours=1))
    notification_service = FakeTelegramNotificationService()
    offer = SimpleNamespace(id=501, carrier_id=601)
    distribution_result = SimpleNamespace(
        offers=[offer],
        matching_reason=MatchingReason.MATCH_FOUND,
        matching_regions=["Lisboa"],
    )
    distribution_call = AsyncMock(return_value=distribution_result)

    service = RequestSubmissionService(
        job_repository=repository,
        carrier_repository=SimpleNamespace(),
        bot=SimpleNamespace(),
        telegram_notification_service=notification_service,
    )

    with patch.object(
        OfferDistributionService,
        "create_offer_distribution_for_job",
        new=distribution_call,
    ):
        result = await service.submit_existing_job(
            job_id=repository.job.id,
            comment=None,
            client_telegram_user_id=repository.job.client_telegram_user_id,
            enforce_telegram_client_limits=True,
        )

    distribution_call.assert_awaited_once()
    assert result.offers_count == 1
    assert result.queued_count == 1
    assert result.sent_count == 0
    assert result.job.short_lead_time_filtered is False
    assert repository.committed
    assert len(notification_service.carrier_notifications) == 1


def assert_policy_wiring() -> None:
    runtime_paths = (
        "app/services/request_submission.py",
        "app/services/offer_expiry.py",
        "app/bot/handlers/job_offer_response.py",
        "app/services/assignment_confirmation.py",
    )
    for relative_path in runtime_paths:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "hold_short_lead_job_for_manual_review" not in source, relative_path

    escalation_source = (
        PROJECT_ROOT / "app/services/job_escalation.py"
    ).read_text(encoding="utf-8")
    warning_source = (
        PROJECT_ROOT / "app/services/short_lead_time_warning.py"
    ).read_text(encoding="utf-8")
    assert "def hold_short_lead_job_for_manual_review" not in escalation_source
    assert "def should_filter_short_lead_time" not in warning_source

    carrier_approval = (
        PROJECT_ROOT / "app/bot/handlers/carrier_moderation_submit.py"
    ).read_text(encoding="utf-8")
    assert ".where(Job.requested_date >= now)" in carrier_approval
    assert "timedelta(hours=72)" not in carrier_approval
    assert "job.short_lead_time_filtered = False" in carrier_approval

    distribution_source = (
        PROJECT_ROOT / "app/services/offer_distribution.py"
    ).read_text(encoding="utf-8")
    assert "job.short_lead_time_filtered = False" in distribution_source

    request_update = (
        PROJECT_ROOT / "app/services/request_update.py"
    ).read_text(encoding="utf-8")
    assert "short_lead_time_filtered=False" in request_update

    model_source = (PROJECT_ROOT / "app/models/job.py").read_text(encoding="utf-8")
    migration_source = (
        PROJECT_ROOT
        / "migrations/versions/20260903_1200_filter_short_lead_requests.py"
    ).read_text(encoding="utf-8")
    assert "short_lead_time_filtered" in model_source
    assert "short_lead_time_filtered" in migration_source


async def main() -> None:
    assert_policy_wiring()
    await exercise_urgent_submission_distribution()
    print("SHORT_LEAD_DISTRIBUTION_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
