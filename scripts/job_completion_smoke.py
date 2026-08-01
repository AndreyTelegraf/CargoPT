import asyncio
from datetime import UTC
from datetime import datetime
from types import SimpleNamespace

from app.services.job_completion import COMPLETION_CONFIRMED
from app.services.job_completion import record_completion_response
from app.services.job_lifecycle import InvalidJobStatusTransitionError


class FakeJobRepository:
    def __init__(self, job):
        self.job = job

    async def get_job_by_id(self, job_id):
        return self.job if self.job.id == job_id else None

    async def record_completion_status(self, *, actor, status, updated_at, **kwargs):
        setattr(self.job, f"{actor}_completion_status", status)
        self.job.updated_at = updated_at
        return self.job

    async def update_job_status(self, *, status, updated_at, **kwargs):
        self.job.status = str(status)
        self.job.completed_at = updated_at
        return self.job


async def main():
    now = datetime.now(UTC)
    job = SimpleNamespace(
        id=138,
        status="assigned",
        completion_prompted_at=now,
        client_completion_status=None,
        carrier_completion_status=None,
        completed_at=None,
        updated_at=now,
    )
    repository = FakeJobRepository(job)
    await record_completion_response(
        repository,
        job_id=138,
        actor="client",
        status=COMPLETION_CONFIRMED,
        now=now,
    )
    assert job.status == "assigned"
    await record_completion_response(
        repository,
        job_id=138,
        actor="carrier",
        status=COMPLETION_CONFIRMED,
        now=now,
    )
    assert job.status == "completed"
    assert job.completed_at == now

    job.status = "offered"
    try:
        await record_completion_response(
            repository,
            job_id=138,
            actor="client",
            status=COMPLETION_CONFIRMED,
            now=now,
        )
    except InvalidJobStatusTransitionError:
        pass
    else:
        raise AssertionError("completion from offered status was accepted")

    print("JOB_COMPLETION_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
