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

from app.bot.assignment_confirmation_keyboard import build_assignment_confirmation_keyboard
from app.services.assignment_confirmation import build_assignment_result_text
from app.services.assignment_confirmation import parse_assignment_callback
from app.domain.carrier_status import CarrierStatus
from app.domain.job_offer_status import JobOfferStatus
from app.domain.job_status import JobStatus
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import ASSIGNMENT_CONFIRMATION_CONFIRMED
from app.services.assignment_confirmation import ASSIGNMENT_CONFIRMATION_FAILED
from app.services.assignment_confirmation import record_assignment_confirmation
from app.services.job_offer import JobOfferService

DATA_DIR = PROJECT_ROOT / ".tmp_job_assignment_confirmation_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_job_assignment_confirmation_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def build_assigned_pending_pair(session, *, carrier_telegram_user_id: int):
    now = datetime.now(UTC)
    carrier_repo = CarrierRepository(session)
    job_repo = JobRepository(session)

    carrier = await carrier_repo.create_carrier(
        CarrierCompany(
            company_name="Confirmation Carrier",
            contact_name=None,
            phone=None,
            telegram_user_id=carrier_telegram_user_id,
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
            client_telegram_user_id=9001,
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
    return job_repo, job.id


async def exercise_assignment_confirmation() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        job_repo, job_id = await build_assigned_pending_pair(
            session,
            carrier_telegram_user_id=6001,
        )
        after_client = await record_assignment_confirmation(
            job_repo,
            job_id=job_id,
            actor="client",
            status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
        )

        if after_client.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
            raise SystemExit(f"unexpected status after first confirm: {after_client.status}")
        if after_client.client_confirmation_status != ASSIGNMENT_CONFIRMATION_CONFIRMED:
            raise SystemExit("client vote was not stored")

        after_carrier = await record_assignment_confirmation(
            job_repo,
            job_id=job_id,
            actor="carrier",
            status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
        )

        if after_carrier.status != JobStatus.ASSIGNED:
            raise SystemExit(f"unexpected status after both confirm: {after_carrier.status}")
        if after_carrier.carrier_confirmation_status != ASSIGNMENT_CONFIRMATION_CONFIRMED:
            raise SystemExit("carrier vote was not stored")

        await session.commit()

    async with session_maker() as session:
        job_repo, job_id = await build_assigned_pending_pair(
            session,
            carrier_telegram_user_id=6002,
        )
        after_fail = await record_assignment_confirmation(
            job_repo,
            job_id=job_id,
            actor="carrier",
            status=ASSIGNMENT_CONFIRMATION_FAILED,
        )

        if after_fail.status != JobStatus.READY_FOR_MATCHING:
            raise SystemExit(f"unexpected status after fail: {after_fail.status}")
        if after_fail.client_confirmation_status is not None:
            raise SystemExit("client vote was not cleared")
        if after_fail.carrier_confirmation_status is not None:
            raise SystemExit("carrier vote was not cleared")

        accepted = await job_repo.get_accepted_offer_by_job_id(job_id)
        if accepted is not None:
            raise SystemExit("accepted offer must be cancelled after fail")

        offers = await job_repo.list_offers_by_job(job_id)
        statuses = [offer.status for offer in offers]
        if JobOfferStatus.CANCELLED not in statuses:
            raise SystemExit(f"cancelled offer missing after fail: {statuses}")

        await session.commit()

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "job-assignment-confirmation-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    keyboard = build_assignment_confirmation_keyboard(123)
    assert keyboard.inline_keyboard[0][0].callback_data == "assignment:confirm:123"
    assert keyboard.inline_keyboard[0][1].callback_data == "assignment:fail:123"
    assert parse_assignment_callback("assignment:confirm:123") == ("confirm", 123)
    assert parse_assignment_callback("assignment:fail:123") == ("fail", 123)
    assert "ожидаем" not in build_assignment_result_text(
        job_id=123,
        action="confirm",
        job_status=JobStatus.ASSIGNED,
    )

    redispatch_text = build_assignment_result_text(
        job_id=123,
        action="fail",
        job_status=JobStatus.READY_FOR_MATCHING,
    )
    assert redispatch_text == (
        "🟡 Статус\n"
        "По заявке №123 договориться с перевозчиком не удалось.\n\n"
        "Заявка снова в поиске. "
        "Мы отправляем её другим подходящим перевозчикам."
    )
    assert "🔴" not in redispatch_text

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_assignment_confirmation())
    shutil.rmtree(DATA_DIR)

    print("JOB_ASSIGNMENT_CONFIRMATION_SMOKE_OK")


if __name__ == "__main__":
    main()
