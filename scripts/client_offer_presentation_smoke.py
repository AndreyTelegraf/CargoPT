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
from app.domain.job_status import JobStatus
from app.models.carrier import CarrierCompany
from app.models.carrier import CarrierVehicle
from app.models.job import Job
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.client_offer_presentation import ClientOfferPresentationService
from app.services.job_offer import JobOfferService

DATA_DIR = PROJECT_ROOT / ".tmp_client_offer_presentation_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_client_offer_presentation_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def create_carrier_with_vehicle(
    carrier_repo: CarrierRepository,
    *,
    company_name: str,
    telegram_user_id: int,
    telegram_username: str,
    payload_kg: int,
    volume_m3: float,
    max_loaders: int,
    now,
):
    carrier = await carrier_repo.create_carrier(
        CarrierCompany(
            company_name=company_name,
            contact_name="Contact " + company_name,
            phone="+351900000000",
            telegram_user_id=telegram_user_id,
            telegram_username=telegram_username,
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
            payload_kg=payload_kg,
            volume_m3=volume_m3,
            max_loaders=max_loaders,
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


async def exercise_client_offer_presentation() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        carrier_repo = CarrierRepository(session)
        job_repo = JobRepository(session)
        offer_service = JobOfferService(job_repo)
        presentation = ClientOfferPresentationService(
            job_repository=job_repo,
            carrier_repository=carrier_repo,
        )

        first_carrier, first_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            company_name="First Accepted Carrier",
            telegram_user_id=8001,
            telegram_username="first_carrier",
            payload_kg=1200,
            volume_m3=14.0,
            max_loaders=2,
            now=now,
        )
        first_carrier.public_name = "First Public Carrier"
        first_carrier.experience_since_year = 2018
        first_carrier.logo_file_name = "carrier_1.jpg"
        first_carrier.publication_consent_at = now

        second_carrier, second_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            company_name="Second Accepted Carrier",
            telegram_user_id=8002,
            telegram_username="second_carrier",
            payload_kg=1800,
            volume_m3=20.0,
            max_loaders=3,
            now=now,
        )
        second_carrier.public_name = "Hidden Without Consent"
        second_carrier.experience_since_year = 2020
        second_carrier.logo_file_name = "carrier_2.jpg"
        _, pending_vehicle = await create_carrier_with_vehicle(
            carrier_repo,
            company_name="Pending Carrier",
            telegram_user_id=8003,
            telegram_username="pending_carrier",
            payload_kg=900,
            volume_m3=10.0,
            max_loaders=1,
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

        first_offer = await offer_service.create_offer(
            job_id=job.id,
            vehicle=first_vehicle,
            expires_in_minutes=30,
        )
        second_offer = await offer_service.create_offer(
            job_id=job.id,
            vehicle=second_vehicle,
            expires_in_minutes=30,
        )
        pending_offer = await offer_service.create_offer(
            job_id=job.id,
            vehicle=pending_vehicle,
            expires_in_minutes=30,
        )

        await offer_service.accept_offer_without_assignment(first_offer.id)
        await offer_service.accept_offer_without_assignment(second_offer.id)

        views = await presentation.list_accepted_offer_views(job.id)

        if len(views) != 2:
            raise SystemExit(f"unexpected accepted offer view count: {len(views)}")

        offer_ids = {view.offer_id for view in views}
        if first_offer.id not in offer_ids or second_offer.id not in offer_ids:
            raise SystemExit(f"missing accepted offer ids: {offer_ids}")

        if pending_offer.id in offer_ids:
            raise SystemExit("pending offer leaked into accepted offer views")

        first_view = next(view for view in views if view.offer_id == first_offer.id)
        second_view = next(view for view in views if view.offer_id == second_offer.id)

        if first_view.company_name != "First Public Carrier":
            raise SystemExit(f"bad first company: {first_view.company_name}")

        if first_view.operating_regions != "Lisboa":
            raise SystemExit("public operating regions missing")

        if first_view.experience_since_year != 2018:
            raise SystemExit("public experience year missing")

        if first_view.logo_file_name != "carrier_1.jpg":
            raise SystemExit("public logo missing")

        if first_view.telegram_username != "first_carrier":
            raise SystemExit(f"bad first username: {first_view.telegram_username}")

        if first_view.payload_kg != 1200 or first_view.volume_m3 != 14.0:
            raise SystemExit("bad first vehicle capacity")

        if first_view.max_loaders != 2:
            raise SystemExit(f"bad first max_loaders: {first_view.max_loaders}")

        if second_view.company_name != "Second Accepted Carrier":
            raise SystemExit(f"bad second company: {second_view.company_name}")

        if second_view.experience_since_year is not None:
            raise SystemExit("unconsented experience leaked")

        if second_view.logo_file_name is not None:
            raise SystemExit("unconsented logo leaked")

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "client-offer-presentation-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_client_offer_presentation())
    shutil.rmtree(DATA_DIR)

    print("CLIENT_OFFER_PRESENTATION_SMOKE_OK")


if __name__ == "__main__":
    main()
