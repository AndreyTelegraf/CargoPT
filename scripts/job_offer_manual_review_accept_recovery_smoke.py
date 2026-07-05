import asyncio
import os
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
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
from app.services.job_escalation import escalate_job_to_manual_review
from app.services.job_offer import JobOfferService

DATA_DIR = PROJECT_ROOT / ".tmp_job_offer_manual_review_accept_recovery_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_job_offer_manual_review_accept_recovery_smoke/cargopt_dev.db"


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


async def exercise() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        carrier_repo = CarrierRepository(session)
        job_repo = JobRepository(session)
        offer_service = JobOfferService(job_repo)

        carrier = await carrier_repo.create_carrier(
            CarrierCompany(
                company_name="Recovery Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=7701,
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
                vehicle_type="Van",
                payload_kg=1400,
                volume_m3=11.0,
                has_tail_lift=False,
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
                client_telegram_user_id=9001,
                status=JobStatus.MANUAL_REVIEW_REQUIRED,
                requested_date=None,
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                required_loaders=1,
                estimated_payload_kg=500,
                estimated_volume_m3=3.0,
                comment=None,
                created_at=now,
                updated_at=now,
            )
        )

        offer = await offer_service.create_offer(
            job_id=job.id,
            vehicle=vehicle,
            expires_in_minutes=60,
        )

        accepted = await offer_service.accept_offer_without_assignment(offer.id)
        loaded_job = await job_repo.get_job_by_id(job.id)
        loaded_offer = await job_repo.get_offer_by_id(offer.id)

        if accepted.status != JobOfferStatus.ACCEPTED:
            raise SystemExit(f"accepted offer returned wrong status: {accepted.status}")
        if loaded_offer.status != JobOfferStatus.ACCEPTED:
            raise SystemExit(f"stored offer wrong status: {loaded_offer.status}")
        if loaded_job.status != JobStatus.OFFERED:
            raise SystemExit(f"manual review job was not recovered to offered: {loaded_job.status}")

        fake_bot = FakeBot()
        await escalate_job_to_manual_review(
            bot=fake_bot,
            job=loaded_job,
            job_repository=job_repo,
        )

        loaded_after_escalation = await job_repo.get_job_by_id(job.id)
        if loaded_after_escalation.status != JobStatus.OFFERED:
            raise SystemExit(
                f"accepted-offer job was escalated back to manual review: {loaded_after_escalation.status}"
            )
        if fake_bot.sent_messages:
            raise SystemExit("manual review notification was sent for accepted-offer job")

        await session.commit()

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "job-offer-manual-review-accept-recovery-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise())
    shutil.rmtree(DATA_DIR)

    print("JOB_OFFER_MANUAL_REVIEW_ACCEPT_RECOVERY_SMOKE_OK")


if __name__ == "__main__":
    main()
