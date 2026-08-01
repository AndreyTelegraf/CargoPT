from collections.abc import Awaitable
from collections.abc import Callable
from typing import TypeVar
from datetime import UTC
from datetime import datetime

from app.db.session import async_session_maker
from app.repositories.job import JobRepository
from app.services.request_update import RequestUpdateService

T = TypeVar("T")


async def run_request_update(
    operation: Callable[[RequestUpdateService], Awaitable[T]],
) -> T:
    async with async_session_maker() as session:
        repository = JobRepository(session)
        service = RequestUpdateService(job_repository=repository)

        result = await operation(service)

        await session.commit()

    return result


async def persist_draft_step(*, job_id: int, draft_step: str) -> None:
    async with async_session_maker() as session:
        repository = JobRepository(session)
        await repository.update_draft_step(
            job_id=job_id,
            draft_step=draft_step,
            updated_at=datetime.now(UTC),
        )
        await session.commit()
