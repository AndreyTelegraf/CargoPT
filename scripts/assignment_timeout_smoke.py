import asyncio
import os
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.carrier_status import CarrierStatus
from app.domain.job_offer_status import JobOfferStatus
from app.domain.job_status import JobStatus
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_timeout import process_stale_assignment_confirmations
from app.services.job_offer import JobOfferService

DATA_DIR = PROJECT_ROOT / ".tmp_assignment_timeout_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_assignment_timeout_smoke/cargopt_dev.db"


class FakeBot:
    def __init__(self):
        self.sent_messages = []

    async def send_message(self, *, chat_id, text):
        self.sent_messages.append((chat_id, text))


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def create_assigned_pending_job(session, *, stale: bool):
    now = datetime.now(UTC)
    carrier_repo = CarrierRepository(session)
    job_repo = JobRepository(session)

    carrier = await carrier_repo.create_carrier(
        CarrierCompany(
            company_name="Timeout Carrier",
            contact_name=None,
            phone=None,
            telegram_user_id=6101 if stale else 6102,
            status=CarrierStatus.PROFILE_COMPLETED,
            paid_until=None,
            assembly_required=False,
            packing_required=False,
            operating_regions="Lisboa",
            profile_completed_at=now,
            current_profile_step=None,
            internal_note=None,
            created_at=now,
            updated_at=now,
        )
    )

    vehicle = await carrier_repo.create_vehicle(
        CarrierVehicle(
            carrier_id=carrier.id,
            vehicle_type="large_van",
            payload_kg=1600,
            volume_m3=18.0,
            has_tail_lift=True,
            has_crane=False,
            has_mobile_lift=False,
            mobile_lift_max_floor=None,
            mobile_lift_max_weight_kg=None,
            crane_max_weight_kg=None,
            crane_reach_meters=None,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )

    job = await job_repo.create_job(
        Job(
            client_telegram_user_id=9101 if stale else 9102,
            status=JobStatus.MATCHING,
            requested_date=None,
            assigned_at=None,
            started_at=None,
            completed_at=None,
            cancelled_at=None,
            client_confirmation_status=None,
            carrier_confirmation_status=None,
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=True,
            needs_crane=False,
            needs_mobile_lift=False,
            required_loaders=None,
            estimated_payload_kg=1000,
            estimated_volume_m3=12.0,
            comment=None,
            created_at=now,
            updated_at=now,
        )
    )

    service = JobOfferService(job_repo)
    offer = await service.create_offer(
        job_id=job.id,
        vehicle=vehicle,
        expires_in_minutes=30,
    )
    await service.accept_offer_and_assign_job(offer.id)

    if stale:
        loaded = await job_repo.get_job_by_id(job.id)
        loaded.assigned_at = now - timedelta(hours=25)
        loaded.updated_at = now - timedelta(hours=25)
        await session.flush()

    return job.id


async def exercise() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        stale_job_id = await create_assigned_pending_job(session, stale=True)
        fresh_job_id = await create_assigned_pending_job(session, stale=False)

        fake_bot = FakeBot()
        processed = await process_stale_assignment_confirmations(
            bot=fake_bot,
            session=session,
            timeout_hours=24,
        )

        if processed != 1:
            raise SystemExit(f"expected 1 processed stale job, got {processed}")

        job_repo = JobRepository(session)
        stale_job = await job_repo.get_job_by_id(stale_job_id)
        fresh_job = await job_repo.get_job_by_id(fresh_job_id)

        if stale_job.status == JobStatus.ASSIGNED_PENDING_CONFIRMATION:
            raise SystemExit("stale job stayed in assigned_pending_confirmation")

        if fresh_job.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
            raise SystemExit(f"fresh job was changed unexpectedly: {fresh_job.status}")

        offers = await job_repo.list_offers_by_job(stale_job_id)
        statuses = [offer.status for offer in offers]
        if JobOfferStatus.CANCELLED not in statuses:
            raise SystemExit(f"cancelled offer missing: {statuses}")

        if len(fake_bot.sent_messages) != 2:
            raise SystemExit(f"expected 2 timeout notifications, got {len(fake_bot.sent_messages)}")

        messages_by_chat = dict(fake_bot.sent_messages)
        client_text = messages_by_chat.get(9101)
        carrier_text = messages_by_chat.get(6101)

        expected_client_text = (
            "🟡 Статус\n"
            f"По заявке №{stale_job_id} подтверждение не было получено вовремя.\n\n"
            "Заявка снова в поиске. "
            "Мы отправляем её другим подходящим перевозчикам."
        )
        expected_carrier_text = (
            "🔴 Статус\n"
            f"По заявке №{stale_job_id} подтверждение не было получено вовремя.\n\n"
            "Для вас эта заявка закрыта."
        )

        if client_text != expected_client_text:
            raise SystemExit(f"unexpected client timeout text: {client_text!r}")
        if carrier_text != expected_carrier_text:
            raise SystemExit(f"unexpected carrier timeout text: {carrier_text!r}")

        await session.commit()

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "assignment-timeout-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise())
    shutil.rmtree(DATA_DIR)

    print("ASSIGNMENT_TIMEOUT_SMOKE_OK")


if __name__ == "__main__":
    main()
