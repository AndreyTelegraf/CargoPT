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
from app.services.job_offer import ClientOfferSelectionError
from app.services.job_offer import JobOfferService

DATA_DIR = PROJECT_ROOT / ".tmp_client_offer_selection_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_client_offer_selection_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def create_carrier_with_vehicle(carrier_repo, *, name: str, telegram_user_id: int, now):
    carrier = await carrier_repo.create_carrier(
        CarrierCompany(
            company_name=name,
            contact_name=None,
            phone=None,
            telegram_user_id=telegram_user_id,
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

    return carrier, vehicle


async def exercise_client_offer_selection() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        carrier_repo = CarrierRepository(session)
        job_repo = JobRepository(session)
        service = JobOfferService(job_repo)

        _, first_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            name="Selected Carrier",
            telegram_user_id=7001,
            now=now,
        )
        _, second_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            name="Cancelled Carrier",
            telegram_user_id=7002,
            now=now,
        )
        _, third_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            name="Declined Pending Carrier",
            telegram_user_id=7003,
            now=now,
        )

        job = await job_repo.create_job(
            Job(
                client_telegram_user_id=9001,
                status=JobStatus.MATCHING,
                requested_date=None,
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

        selected_offer = await service.create_offer(
            job_id=job.id,
            vehicle=first_vehicle,
            expires_in_minutes=30,
        )
        other_accepted_offer = await service.create_offer(
            job_id=job.id,
            vehicle=second_vehicle,
            expires_in_minutes=30,
        )
        pending_offer = await service.create_offer(
            job_id=job.id,
            vehicle=third_vehicle,
            expires_in_minutes=30,
        )

        selected_offer = await service.accept_offer_without_assignment(selected_offer.id)
        other_accepted_offer = await service.accept_offer_without_assignment(other_accepted_offer.id)

        loaded_pending_before = await job_repo.get_offer_by_id(pending_offer.id)
        if loaded_pending_before.status != JobOfferStatus.PENDING:
            raise SystemExit(f"unexpected pending status before selection: {loaded_pending_before.status}")

        selected = await service.select_accepted_offer_for_client(
            job_id=job.id,
            offer_id=selected_offer.id,
        )

        await session.commit()

        loaded_job = await job_repo.get_job_by_id(job.id)
        loaded_selected = await job_repo.get_offer_by_id(selected_offer.id)
        loaded_other_accepted = await job_repo.get_offer_by_id(other_accepted_offer.id)
        loaded_pending = await job_repo.get_offer_by_id(pending_offer.id)

        if selected.id != selected_offer.id:
            raise SystemExit("wrong selected offer returned")

        if loaded_selected.status != JobOfferStatus.ACCEPTED:
            raise SystemExit(f"selected offer status changed unexpectedly: {loaded_selected.status}")

        if loaded_other_accepted.status != JobOfferStatus.CANCELLED:
            raise SystemExit(f"unselected accepted offer was not cancelled: {loaded_other_accepted.status}")

        if loaded_pending.status != JobOfferStatus.DECLINED:
            raise SystemExit(f"unselected pending offer was not declined: {loaded_pending.status}")

        if loaded_job.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
            raise SystemExit(f"unexpected job status: {loaded_job.status}")

        if loaded_job.assigned_at is None:
            raise SystemExit("assigned_at missing")

        try:
            await service.select_accepted_offer_for_client(
                job_id=job.id,
                offer_id=selected_offer.id,
            )
        except ClientOfferSelectionError:
            pass
        else:
            raise SystemExit("second client selection unexpectedly succeeded")

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "client-offer-selection-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_client_offer_selection())
    shutil.rmtree(DATA_DIR)

    print("CLIENT_OFFER_SELECTION_SMOKE_OK")


if __name__ == "__main__":
    main()
