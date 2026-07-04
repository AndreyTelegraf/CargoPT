import asyncio
from datetime import UTC
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.job_status import JobStatus
from app.models.job import Job
from app.repositories.job import JobRepository


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Job.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        repo = JobRepository(session)
        now = datetime.now(UTC)
        job = await repo.create_job(
            Job(
                client_telegram_user_id=None,
                client_telegram_username=None,
                source="smoke",
                source_locale=None,
                customer_name=None,
                customer_email=None,
                preferred_contact=None,
                client_phone=None,
                client_whatsapp=None,
                utm_source=None,
                utm_campaign=None,
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
        )

        assert job.tracking_token
        loaded = await repo.get_job_by_tracking_token(job.tracking_token)
        assert loaded is not None
        assert loaded.id == job.id

        missing = await repo.get_job_by_tracking_token("missing-token")
        assert missing is None

    await engine.dispose()
    print("job_tracking_read_api_ok")


if __name__ == "__main__":
    asyncio.run(main())
