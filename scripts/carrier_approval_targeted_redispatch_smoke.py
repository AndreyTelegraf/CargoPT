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
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.bot.handlers.carrier_moderation_submit import (
    redispatch_open_jobs_to_new_carrier,
)
from app.db.base import Base
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.models.job import JobAddress
from app.models.job import JobOffer


class FakeBot:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, *, chat_id, text, **kwargs):
        message = SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            message_id=9000 + len(self.messages),
        )
        self.messages.append((chat_id, text, kwargs))
        return message


def make_carrier(*, carrier_id: int, telegram_user_id: int, now: datetime):
    carrier = CarrierCompany(
        id=carrier_id,
        company_name=f"Carrier {carrier_id}",
        telegram_user_id=telegram_user_id,
        telegram_username=f"carrier_{carrier_id}",
        status="active",
        paid_until=now + timedelta(days=30),
        assembly_required=False,
        packing_required=False,
        operating_regions="all_portugal",
        profile_completed_at=now,
        current_profile_step="completed",
        created_at=now,
        updated_at=now,
    )
    vehicle = CarrierVehicle(
        id=carrier_id,
        carrier_id=carrier_id,
        vehicle_type="Carrinha",
        payload_kg=1500,
        volume_m3=15,
        max_loaders=2,
        has_tail_lift=False,
        has_crane=False,
        has_mobile_lift=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    return carrier, vehicle


def make_job(*, job_id: int, requested_date: datetime | None, now: datetime):
    return Job(
        id=job_id,
        tracking_token=f"token-{job_id}",
        source="smoke",
        status="no_carriers_found",
        requested_date=requested_date,
        needs_assembly=False,
        needs_packing=False,
        needs_tail_lift=False,
        needs_crane=False,
        needs_mobile_lift=False,
        created_at=now,
        updated_at=now,
    )


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with sessions() as session:
        target_carrier, target_vehicle = make_carrier(
            carrier_id=101,
            telegram_user_id=5001,
            now=now,
        )
        other_carrier, other_vehicle = make_carrier(
            carrier_id=202,
            telegram_user_id=5002,
            now=now,
        )
        session.add_all(
            [
                target_carrier,
                target_vehicle,
                other_carrier,
                other_vehicle,
            ]
        )

        future_job = make_job(
            job_id=1,
            requested_date=now + timedelta(days=3),
            now=now,
        )
        past_job = make_job(
            job_id=2,
            requested_date=now - timedelta(days=3),
            now=now,
        )
        missing_date_job = make_job(
            job_id=3,
            requested_date=None,
            now=now,
        )
        existing_offer_job = make_job(
            job_id=4,
            requested_date=now + timedelta(days=4),
            now=now,
        )
        session.add_all(
            [
                future_job,
                past_job,
                missing_date_job,
                existing_offer_job,
            ]
        )
        await session.flush()

        for job in (
            future_job,
            past_job,
            missing_date_job,
            existing_offer_job,
        ):
            session.add(
                JobAddress(
                    job_id=job.id,
                    kind="pickup",
                    raw_text="Lisboa",
                    latitude=38.72,
                    longitude=-9.14,
                    created_at=now,
                )
            )

        session.add(
            JobOffer(
                job_id=existing_offer_job.id,
                carrier_id=target_carrier.id,
                vehicle_id=target_vehicle.id,
                status="expired",
                offered_at=now - timedelta(days=1),
                expires_at=now - timedelta(hours=23),
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(hours=23),
            )
        )
        await session.flush()

        bot = FakeBot()
        created, sent = await redispatch_open_jobs_to_new_carrier(
            bot=bot,
            session=session,
            carrier_id=target_carrier.id,
        )

        offers = list(
            (
                await session.scalars(
                    select(JobOffer).order_by(JobOffer.id)
                )
            ).all()
        )

        assert created == 1
        assert sent == 1
        assert len(offers) == 2
        new_offer = offers[-1]
        assert new_offer.job_id == future_job.id
        assert new_offer.carrier_id == target_carrier.id
        assert all(offer.carrier_id != other_carrier.id for offer in offers)
        assert bot.messages[0][0] == target_carrier.telegram_user_id

    await engine.dispose()
    print("CARRIER_APPROVAL_TARGETED_REDISPATCH_OK")


if __name__ == "__main__":
    asyncio.run(main())
