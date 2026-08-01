import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models import carrier as carrier_models  # noqa: F401
from app.models.job import JobOffer
from app.repositories.job import JobRepository


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        statuses = (
            (1, "pending"),
            (2, "accepted"),
            (3, "expired"),
            (4, "declined"),
            (5, "cancelled"),
        )
        for carrier_id, status in statuses:
            session.add(
                JobOffer(
                    job_id=138,
                    carrier_id=carrier_id,
                    vehicle_id=carrier_id,
                    status=status,
                    offered_at=now,
                    responded_at=None if status == "pending" else now,
                    expires_at=now + timedelta(hours=1),
                    carrier_note=None,
                    decline_reason=None,
                    price_cents=None,
                    carrier_message_chat_id=None,
                    carrier_message_id=None,
                    created_at=now,
                    updated_at=now,
                )
            )
        await session.commit()

        repository = JobRepository(session)
        all_carrier_ids = await repository.list_offer_carrier_ids_by_job(138)
        active_carrier_ids = await repository.list_active_offer_carrier_ids_by_job(138)

        assert all_carrier_ids == {1, 2, 3, 4, 5}
        assert active_carrier_ids == {1, 2}
        assert {3, 4, 5}.isdisjoint(active_carrier_ids)

    await engine.dispose()
    print("MANUAL_OFFER_REDISPATCH_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
