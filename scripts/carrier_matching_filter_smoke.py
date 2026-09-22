import asyncio
import os
import shutil
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
from app.domain.carrier_status import CarrierStatus
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierMatchingFilter
from app.models.carrier import CarrierVehicle
from app.repositories.carrier import CarrierRepository
from app.services.carrier_search import CarrierSearchService

DATA_DIR = PROJECT_ROOT / ".tmp_carrier_matching_filter_smoke"
DATABASE_URL = (
    "sqlite+aiosqlite:///.tmp_carrier_matching_filter_smoke/cargopt_dev.db"
)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def add_carrier(
    repository: CarrierRepository,
    *,
    telegram_user_id: int,
    name: str,
    now: datetime,
) -> CarrierCompany:
    carrier = await repository.create_carrier(
        CarrierCompany(
            company_name=name,
            contact_name=None,
            phone=None,
            telegram_user_id=telegram_user_id,
            status=CarrierStatus.ACTIVE,
            paid_until=now + timedelta(days=30),
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
    await repository.create_vehicle(
        CarrierVehicle(
            carrier_id=carrier.id,
            vehicle_type="van",
            payload_kg=2000,
            volume_m3=20.0,
            max_loaders=3,
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
    return carrier


async def exercise_filter() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        repository = CarrierRepository(session)
        regular = await add_carrier(
            repository,
            telegram_user_id=5101,
            name="Regular Carrier",
            now=now,
        )
        filtered = await add_carrier(
            repository,
            telegram_user_id=5102,
            name="Small Jobs Carrier",
            now=now,
        )
        session.add(
            CarrierMatchingFilter(
                carrier_id=filtered.id,
                max_job_volume_m3=6.7,
                require_known_volume=True,
                no_loaders_only=True,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

        search = CarrierSearchService(repository)

        async def matched_carriers(
            *,
            volume: float | None,
            loaders: int | None,
        ) -> set[int]:
            vehicles = await search.find_matching_vehicles(
                regions=["Lisboa"],
                requested_volume_m3=volume,
                requested_loaders=loaders,
            )
            return {vehicle.carrier_id for vehicle in vehicles}

        small = await matched_carriers(volume=6.7, loaders=0)
        if small != {regular.id, filtered.id}:
            raise SystemExit(f"small loader-free job mismatch: {sorted(small)}")

        unknown = await matched_carriers(volume=None, loaders=0)
        if unknown != {regular.id}:
            raise SystemExit(f"unknown-volume filter mismatch: {sorted(unknown)}")

        too_large = await matched_carriers(volume=6.71, loaders=0)
        if too_large != {regular.id}:
            raise SystemExit(f"maximum-volume filter mismatch: {sorted(too_large)}")

        loaders_required = await matched_carriers(volume=2.0, loaders=1)
        if loaders_required != {regular.id}:
            raise SystemExit(
                f"no-loaders-only filter mismatch: {sorted(loaders_required)}"
            )

        unspecified_loaders = await matched_carriers(volume=2.0, loaders=None)
        if unspecified_loaders != {regular.id, filtered.id}:
            raise SystemExit(
                "unspecified loaders changed current no-loaders semantics: "
                f"{sorted(unspecified_loaders)}"
            )

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "carrier-matching-filter-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    asyncio.run(exercise_filter())
    shutil.rmtree(DATA_DIR)
    print("CARRIER_MATCHING_FILTER_SMOKE_OK")


if __name__ == "__main__":
    main()
