import asyncio
import os
from datetime import UTC
from datetime import datetime
from datetime import timedelta

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ["EMAIL_ENABLED"] = "false"
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/cargopt_dev.db")

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.models.job import JobOffer
from app.services.job_lifecycle_notifications import process_job_lifecycle_notifications


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


async def main():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)

    async with sessions() as session:
        session.add(
            CarrierCompany(
                id=1,
                company_name="Lifecycle Carrier",
                telegram_user_id=9001,
                status="active",
                assembly_required=False,
                packing_required=False,
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            CarrierVehicle(
                id=1,
                carrier_id=1,
                vehicle_type="Van",
                has_tail_lift=False,
                has_crane=False,
                has_mobile_lift=False,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        jobs = (
            Job(
                id=201,
                client_telegram_user_id=8001,
                status="assigned",
                requested_date=now + timedelta(hours=12),
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                created_at=now,
                updated_at=now,
            ),
            Job(
                id=202,
                client_telegram_user_id=8002,
                status="assigned",
                requested_date=now + timedelta(hours=1),
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                created_at=now,
                updated_at=now,
            ),
            Job(
                id=203,
                client_telegram_user_id=8003,
                status="in_progress",
                requested_date=now - timedelta(hours=3),
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                created_at=now - timedelta(days=1),
                updated_at=now,
            ),
        )
        session.add_all(jobs)
        await session.flush()
        for index, job in enumerate(jobs, start=1):
            session.add(
                JobOffer(
                    job_id=job.id,
                    carrier_id=1,
                    vehicle_id=1,
                    status="accepted",
                    offered_at=now - timedelta(days=1),
                    responded_at=now - timedelta(hours=20),
                    created_at=now - timedelta(days=1),
                    updated_at=now,
                )
            )
        await session.flush()

        bot = FakeBot()
        processed = await process_job_lifecycle_notifications(
            bot=bot,
            session=session,
            now=now,
        )
        assert processed == 3
        assert jobs[0].reminder_24h_sent_at == now
        assert jobs[0].reminder_2h_sent_at is None
        assert jobs[1].reminder_2h_sent_at == now
        assert jobs[2].completion_prompted_at == now
        assert len(bot.messages) == 6
        completion_messages = [
            message for message in bot.messages if message.get("reply_markup") is not None
        ]
        assert len(completion_messages) == 2

    await engine.dispose()
    print("JOB_LIFECYCLE_NOTIFICATIONS_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
