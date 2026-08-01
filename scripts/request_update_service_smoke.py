import asyncio
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

from app.domain.job_status import JobStatus
from app.domain.requested_date import RequestedDateInPastError
from app.models.job import Job
from app.models.job import JobAddress
from app.models.job import JobItem
from app.services.request_update import RequestUpdateService


class FakeJobRepository:
    def __init__(self):
        self.calls = []

    async def add_address(self, address):
        self.calls.append(("add_address", address.kind, address.raw_text))
        address.id = 101
        return address

    async def update_address_details(self, *, address_id, floor, has_elevator):
        self.calls.append(("update_address_details", address_id, floor, has_elevator))
        return JobAddress(
            id=address_id,
            job_id=1,
            kind="pickup",
            raw_text="Lisboa",
            floor=floor,
            has_elevator=has_elevator,
            created_at=datetime.now(UTC),
        )

    async def add_item(self, item):
        self.calls.append(("add_item", item.description, item.quantity))
        item.id = 201
        return item

    async def get_job_by_id(self, job_id):
        return make_job(job_id=job_id)

    async def update_estimated_payload(self, job_id, estimated_payload_kg, updated_at):
        self.calls.append(("update_estimated_payload", job_id, estimated_payload_kg))
        job = make_job(job_id=job_id)
        job.estimated_payload_kg = estimated_payload_kg
        return job

    async def update_estimated_volume(self, job_id, estimated_volume_m3, updated_at):
        self.calls.append(("update_estimated_volume", job_id, estimated_volume_m3))
        job = make_job(job_id=job_id)
        job.estimated_volume_m3 = estimated_volume_m3
        return job

    async def update_required_loaders(self, job_id, required_loaders, updated_at):
        self.calls.append(("update_required_loaders", job_id, required_loaders))
        job = make_job(job_id=job_id)
        job.required_loaders = required_loaders
        return job

    async def update_needs_assembly(self, job_id, needs_assembly, updated_at):
        self.calls.append(("update_needs_assembly", job_id, needs_assembly))
        job = make_job(job_id=job_id)
        job.needs_assembly = needs_assembly
        return job

    async def update_needs_packing(self, job_id, needs_packing, updated_at):
        self.calls.append(("update_needs_packing", job_id, needs_packing))
        job = make_job(job_id=job_id)
        job.needs_packing = needs_packing
        return job

    async def update_needs_tail_lift(self, job_id, needs_tail_lift, updated_at):
        self.calls.append(("update_needs_tail_lift", job_id, needs_tail_lift))
        job = make_job(job_id=job_id)
        job.needs_tail_lift = needs_tail_lift
        return job

    async def update_needs_crane(self, job_id, needs_crane, updated_at):
        self.calls.append(("update_needs_crane", job_id, needs_crane))
        job = make_job(job_id=job_id)
        job.needs_crane = needs_crane
        return job

    async def update_needs_mobile_lift(self, job_id, needs_mobile_lift, updated_at):
        self.calls.append(("update_needs_mobile_lift", job_id, needs_mobile_lift))
        job = make_job(job_id=job_id)
        job.needs_mobile_lift = needs_mobile_lift
        return job

    async def update_requested_date(self, job_id, requested_date, updated_at):
        self.calls.append(("update_requested_date", job_id, requested_date))
        job = make_job(job_id=job_id)
        job.requested_date = requested_date
        return job

    async def update_client_phone(self, job_id, client_phone, updated_at):
        self.calls.append(("update_client_phone", job_id, client_phone))
        job = make_job(job_id=job_id)
        job.client_phone = client_phone
        return job

    async def add_media(self, media):
        self.calls.append(("add_media", media.job_id, media.media_type))
        media.id = 301
        return media

    async def update_client_whatsapp(self, job_id, client_whatsapp, updated_at):
        self.calls.append(("update_client_whatsapp", job_id, client_whatsapp))
        job = make_job(job_id=job_id)
        job.client_whatsapp = client_whatsapp
        return job


def make_job(*, job_id=1):
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
        client_phone=None,
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
        comment=None,
        created_at=now,
        updated_at=now,
    )


async def main():
    repo = FakeJobRepository()
    service = RequestUpdateService(job_repository=repo)

    address = await service.add_address(
        job_id=1,
        kind="pickup",
        raw_text="Lisboa",
    )
    assert address.id == 101

    await service.update_address_details(
        address_id=101,
        floor=3,
        has_elevator=False,
    )
    await service.add_item(job_id=1, description="Sofa", quantity=None)
    await service.update_estimated_payload(job_id=1, estimated_payload_kg=500)
    await service.update_estimated_volume(job_id=1, estimated_volume_m3=3.0)
    await service.update_required_loaders(job_id=1, required_loaders=2)
    await service.update_needs_assembly(job_id=1, needs_assembly=True)
    await service.update_needs_packing(job_id=1, needs_packing=True)
    await service.update_needs_tail_lift(job_id=1, needs_tail_lift=False)
    await service.update_needs_crane(job_id=1, needs_crane=False)
    await service.update_needs_mobile_lift(job_id=1, needs_mobile_lift=False)
    await service.update_requested_date(
        job_id=1,
        requested_date=datetime.now(UTC) + timedelta(days=1),
    )

    date_update_count = sum(
        call[0] == "update_requested_date" for call in repo.calls
    )
    try:
        await service.update_requested_date(
            job_id=1,
            requested_date=datetime.now(UTC) - timedelta(days=2),
        )
    except RequestedDateInPastError:
        pass
    else:
        raise AssertionError("past requested date must be rejected")
    assert sum(
        call[0] == "update_requested_date" for call in repo.calls
    ) == date_update_count
    await service.update_client_phone(job_id=1, client_phone="+351")
    await service.update_client_whatsapp(job_id=1, client_whatsapp="+351")
    await service.add_media(
        job_id=1,
        telegram_file_id="file",
        media_type="photo",
    )

    names = [call[0] for call in repo.calls]
    expected = {
        "add_address",
        "update_address_details",
        "add_item",
        "update_estimated_payload",
        "update_estimated_volume",
        "update_required_loaders",
        "update_needs_assembly",
        "update_needs_packing",
        "update_needs_tail_lift",
        "update_needs_crane",
        "update_needs_mobile_lift",
        "update_requested_date",
        "update_client_phone",
        "update_client_whatsapp",
        "add_media",
    }
    assert expected.issubset(set(names))

    print("REQUEST_UPDATE_SERVICE_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
