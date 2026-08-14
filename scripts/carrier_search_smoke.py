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
from app.repositories.carrier import CarrierRepository
from app.services.carrier_search import CarrierSearchService

DATA_DIR = PROJECT_ROOT / ".tmp_carrier_search_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_carrier_search_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def exercise_search() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        repo = CarrierRepository(session)

        active = await repo.create_carrier(
            CarrierCompany(
                company_name="Active Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=1001,
                status=CarrierStatus.ACTIVE,
                paid_until=now + timedelta(days=30),
                assembly_required=True,
                packing_required=True,
                operating_regions="Lisboa, Porto",
                profile_completed_at=now,
                current_profile_step=None,
                internal_note=None,
                created_at=now,
                updated_at=now,
            )
        )

        expired = await repo.create_carrier(
            CarrierCompany(
                company_name="Expired Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=1003,
                status=CarrierStatus.ACTIVE,
                paid_until=now - timedelta(days=1),
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

        inactive = await repo.create_carrier(
            CarrierCompany(
                company_name="Draft Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=1002,
                status=CarrierStatus.DRAFT,
                paid_until=None,
                assembly_required=False,
                packing_required=False,
                operating_regions="Lisboa",
                profile_completed_at=None,
                current_profile_step=None,
                internal_note=None,
                created_at=now,
                updated_at=now,
            )
        )

        lisboa_only = await repo.create_carrier(
            CarrierCompany(
                company_name="Lisboa Only Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=1004,
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

        await repo.create_vehicle(
            CarrierVehicle(
                carrier_id=active.id,
                vehicle_type="large_van",
                payload_kg=1200,
                volume_m3=14.0,
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

        await repo.create_vehicle(
            CarrierVehicle(
                carrier_id=expired.id,
                vehicle_type="large_van",
                payload_kg=5000,
                volume_m3=50.0,
                has_tail_lift=True,
                has_crane=True,
                has_mobile_lift=True,
                mobile_lift_max_floor=10,
                mobile_lift_max_weight_kg=500,
                crane_max_weight_kg=2000,
                crane_reach_meters=12,
                max_loaders=6,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        await repo.create_vehicle(
            CarrierVehicle(
                carrier_id=inactive.id,
                vehicle_type="large_van",
                payload_kg=3000,
                volume_m3=30.0,
                has_tail_lift=True,
                has_crane=True,
                has_mobile_lift=True,
                mobile_lift_max_floor=6,
                mobile_lift_max_weight_kg=300,
                crane_max_weight_kg=1000,
                crane_reach_meters=10,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        await repo.create_vehicle(
            CarrierVehicle(
                carrier_id=lisboa_only.id,
                vehicle_type="small_van",
                payload_kg=500,
                volume_m3=5.0,
                has_tail_lift=False,
                has_crane=False,
                has_mobile_lift=False,
                mobile_lift_max_floor=None,
                mobile_lift_max_weight_kg=None,
                crane_max_weight_kg=None,
                crane_reach_meters=None,
                max_loaders=1,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )

        await session.commit()

        search = CarrierSearchService(repo)

        matches = await search.find_matching_vehicles(
            min_payload_kg=1000,
            min_volume_m3=10,
            min_loaders=2,
            needs_tail_lift=True,
            needs_assembly=True,
            needs_packing=True,
        )

        if len(matches) != 1:
            raise SystemExit(f"expected 1 match, got {len(matches)}")

        if matches[0].carrier_id != active.id:
            raise SystemExit("matched wrong carrier")

        route_matches = await search.find_matching_vehicles(
            regions=["Lisboa", "Porto"],
        )
        route_carrier_ids = {vehicle.carrier_id for vehicle in route_matches}
        if route_carrier_ids != {active.id}:
            raise SystemExit(
                "route-wide regions were not required: "
                f"{sorted(route_carrier_ids)}"
            )

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "carrier-search-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_search())
    shutil.rmtree(DATA_DIR)

    print("CARRIER_SEARCH_SMOKE_OK")


if __name__ == "__main__":
    main()
