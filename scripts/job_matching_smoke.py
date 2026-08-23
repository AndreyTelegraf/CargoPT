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
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.models.job import JobAddress
from app.repositories.carrier import CarrierRepository
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService

DATA_DIR = PROJECT_ROOT / ".tmp_job_matching_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_job_matching_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def exercise_job_matching() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        repo = CarrierRepository(session)

        carrier = await repo.create_carrier(
            CarrierCompany(
                company_name="Match Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=2001,
                status=CarrierStatus.ACTIVE,
                paid_until=now + timedelta(days=30),
                assembly_required=True,
                packing_required=True,
                operating_regions="Lisboa",
                profile_completed_at=now,
                current_profile_step=None,
                internal_note=None,
                created_at=now,
                updated_at=now,
            )
        )

        await repo.create_vehicle(
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
                max_loaders=3,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        job = Job(
            client_telegram_user_id=9001,
            status="ready_for_matching",
            requested_date=None,
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=False,
            needs_crane=True,
            needs_mobile_lift=True,
            required_loaders=999,
            estimated_payload_kg=999999,
            estimated_volume_m3=999999.0,
            comment=None,
            created_at=now,
            updated_at=now,
        )

        job.addresses = [
            JobAddress(
                job_id=1,
                kind="pickup",
                raw_text="Rua Augusta 1, Lisboa",
                original_google_maps_url=None,
                normalized_address="Rua Augusta 1, Lisboa",
                city=None,
                postal_code=None,
                floor=None,
                has_elevator=None,
                latitude=None,
                longitude=None,
                map_url=None,
                created_at=now,
            )
        ]

        search = CarrierSearchService(repo)
        matching = JobMatchingService(search)

        matches = await matching.find_matching_vehicles_for_job(job)

        if len(matches) != 1:
            raise SystemExit(
                "expected 1 region-only match despite impossible cargo "
                f"constraints, got {len(matches)}"
            )

        if matches[0].carrier_id != carrier.id:
            raise SystemExit("matched wrong carrier")

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "job-matching-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_job_matching())
    shutil.rmtree(DATA_DIR)

    print("JOB_MATCHING_SMOKE_OK")


if __name__ == "__main__":
    main()
