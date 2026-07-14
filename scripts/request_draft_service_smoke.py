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

from app.domain.job_status import JobStatus
from app.models.job import Job
from app.services.request_draft import ClientBannedError
from app.services.request_draft import RequestDraftService
from app.services.request_draft import draft_has_no_progress


class FakeJobRepository:
    def __init__(self, *, ban=None, latest_draft=None, addresses=None, items=None):
        self.ban = ban
        self.latest_draft = latest_draft
        self.addresses = addresses or []
        self.items = items or []
        self.created = False

    async def get_active_client_ban(self, telegram_user_id):
        return self.ban

    async def get_latest_draft_job_by_client_id(self, telegram_user_id):
        return self.latest_draft

    async def list_addresses_by_job(self, job_id):
        return self.addresses

    async def list_items_by_job(self, job_id):
        return self.items

    async def create_job(self, job):
        self.created = True
        job.id = 1001
        return job


def make_job(*, job_id=1, comment=None, client_phone=None):
    now = datetime.now(UTC)
    return Job(
        id=job_id,
        client_telegram_user_id=123,
        client_telegram_username="client",
        source=None,
        source_locale=None,
        customer_name=None,
        customer_email=None,
        preferred_contact=None,
        client_phone=client_phone,
        client_whatsapp=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        landing_version=None,
        status=JobStatus.DRAFT,
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
        created_at=now,
        updated_at=now,
    )


async def main():
    empty_draft = make_job(job_id=10)
    repo = FakeJobRepository(latest_draft=empty_draft)
    service = RequestDraftService(job_repository=repo)
    result = await service.create_or_reuse_telegram_draft(
        client_telegram_user_id=123,
        client_telegram_username="client",
    )
    assert result.job.id == 10
    assert result.reused_existing_draft is True
    assert repo.created is False

    progressed_draft = make_job(job_id=11, client_phone="+351")
    repo = FakeJobRepository(latest_draft=progressed_draft)
    service = RequestDraftService(job_repository=repo)
    result = await service.create_or_reuse_telegram_draft(
        client_telegram_user_id=123,
        client_telegram_username="client",
    )
    assert result.job.id == 1001
    assert result.reused_existing_draft is False
    assert repo.created is True

    repo = FakeJobRepository(ban=object())
    service = RequestDraftService(job_repository=repo)
    try:
        await service.create_or_reuse_telegram_draft(
            client_telegram_user_id=123,
            client_telegram_username="client",
        )
    except ClientBannedError as exc:
        assert str(exc) == "client_banned"
    else:
        raise AssertionError("banned client did not fail")

    assert draft_has_no_progress(make_job(), [], []) is True
    assert draft_has_no_progress(make_job(client_phone="+351"), [], []) is False

    print("REQUEST_DRAFT_SERVICE_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
