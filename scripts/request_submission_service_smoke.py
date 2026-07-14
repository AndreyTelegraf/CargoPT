import asyncio
import os
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"

from app.models.job import Job
from app.services.request_submission import ClientJobLimitError
from app.services.request_submission import RequestSubmissionService


class FakeJobRepository:
    def __init__(self, active_jobs=0, sent_jobs=0):
        self.active_jobs = active_jobs
        self.sent_jobs = sent_jobs
        self.finalized = False

    async def count_active_client_jobs(self, telegram_user_id):
        return self.active_jobs

    async def count_sent_client_jobs_since(self, telegram_user_id, since):
        return self.sent_jobs

    async def update_comment_and_status(self, *, job_id, comment, status, updated_at):
        self.finalized = True
        return Job(
            id=job_id,
            client_telegram_user_id=telegram_user_id if False else 123,
            client_telegram_username="client",
            source="telegram",
            source_locale=None,
            customer_name=None,
            customer_email=None,
            preferred_contact=None,
            client_phone=None,
            client_whatsapp=None,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            utm_content=None,
            landing_version=None,
            status=status,
            requested_date=None,
            assigned_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            client_confirmation_status=None,
            carrier_confirmation_status=None,
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=False,
            needs_crane=False,
            needs_mobile_lift=False,
            required_loaders=None,
            estimated_payload_kg=None,
            estimated_volume_m3=None,
            comment=comment,
            created_at=datetime.now(UTC),
            updated_at=updated_at,
        )

    async def update_job_status(self, *, job_id, status, updated_at):
        return None

    async def list_offer_carrier_ids_by_job(self, job_id):
        return []

    async def list_addresses_by_job(self, job_id):
        return []

    async def list_media_by_job(self, job_id):
        return []

    async def list_items_by_job(self, job_id):
        return []


class FakeCarrierRepository:
    async def get_carrier_by_vehicle_id(self, vehicle_id):
        return None


class FakeBot:
    async def send_message(self, *args, **kwargs):
        return None


async def assert_limit_errors():
    service = RequestSubmissionService(
        job_repository=FakeJobRepository(active_jobs=2),
        carrier_repository=FakeCarrierRepository(),
        bot=FakeBot(),
    )
    try:
        await service.submit_existing_job(
            job_id=1,
            comment=None,
            client_telegram_user_id=123,
            enforce_telegram_client_limits=True,
        )
    except ClientJobLimitError as exc:
        assert str(exc) == "active_job_limit_reached"
    else:
        raise AssertionError("active job limit did not fail")

    service = RequestSubmissionService(
        job_repository=FakeJobRepository(sent_jobs=3),
        carrier_repository=FakeCarrierRepository(),
        bot=FakeBot(),
    )
    try:
        await service.submit_existing_job(
            job_id=1,
            comment=None,
            client_telegram_user_id=123,
            enforce_telegram_client_limits=True,
        )
    except ClientJobLimitError as exc:
        assert str(exc) == "daily_sent_job_limit_reached"
    else:
        raise AssertionError("daily sent job limit did not fail")


async def main():
    await assert_limit_errors()
    print("REQUEST_SUBMISSION_SERVICE_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
