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
from app.models.job import JobAddress
from app.models.job import JobOffer
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.offer_expiry import process_expired_pending_offers

DATA_DIR = PROJECT_ROOT / ".tmp_offer_expiry_runtime_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_offer_expiry_runtime_smoke/cargopt_dev.db"


class DummyBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, *args, **kwargs):
        self.messages.append((args, kwargs))
        return None

    async def send_photo(self, *args, **kwargs):
        return None

    async def send_video(self, *args, **kwargs):
        return None

    async def send_media_group(self, *args, **kwargs):
        return []


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def exercise_offer_expiry() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        carrier_repo = CarrierRepository(session)
        job_repo = JobRepository(session)

        expired_carrier = await carrier_repo.create_carrier(
            CarrierCompany(
                company_name="Expired Offer Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=3001,
                telegram_username="expired_offer_carrier",
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

        next_carrier = await carrier_repo.create_carrier(
            CarrierCompany(
                company_name="Next Offer Carrier",
                contact_name=None,
                phone=None,
                telegram_user_id=None,
                telegram_username="next_offer_carrier",
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

        expired_vehicle = await carrier_repo.create_vehicle(
            CarrierVehicle(
                carrier_id=expired_carrier.id,
                vehicle_type="van",
                payload_kg=1000,
                volume_m3=10.0,
                max_loaders=2,
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

        await carrier_repo.create_vehicle(
            CarrierVehicle(
                carrier_id=next_carrier.id,
                vehicle_type="van",
                payload_kg=1200,
                volume_m3=12.0,
                max_loaders=2,
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
                client_telegram_username="client",
                client_phone=None,
                client_whatsapp=None,
                status=JobStatus.OFFERED,
                requested_date=None,
                assigned_at=None,
                started_at=None,
                completed_at=None,
                cancelled_at=None,
                client_confirmation_status=None,
                carrier_confirmation_status=None,
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                required_loaders=1,
                estimated_payload_kg=500,
                estimated_volume_m3=5.0,
                comment=None,
                created_at=now,
                updated_at=now,
            )
        )

        await job_repo.add_address(
            JobAddress(
                job_id=job.id,
                kind="pickup",
                raw_text="Lisboa",
                original_google_maps_url=None,
                normalized_address="Lisboa",
                city=None,
                postal_code=None,
                floor=None,
                has_elevator=None,
                latitude=None,
                longitude=None,
                map_url=None,
                created_at=now,
            )
        )

        await job_repo.create_offer(
            JobOffer(
                job_id=job.id,
                carrier_id=expired_carrier.id,
                vehicle_id=expired_vehicle.id,
                status=JobOfferStatus.PENDING,
                offered_at=now - timedelta(hours=2),
                responded_at=None,
                expires_at=now - timedelta(hours=1),
                carrier_note=None,
                price_cents=None,
                carrier_message_chat_id=None,
                carrier_message_id=None,
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
            )
        )

        await session.commit()

        bot = DummyBot()
        processed = await process_expired_pending_offers(
            bot=bot,
            session=session,
        )
        await session.commit()

        if processed != 1:
            raise SystemExit(f"expected 1 processed offer, got {processed}")

        offers = await job_repo.list_offers_by_job(job.id)
        statuses = sorted(offer.status for offer in offers)

        if statuses != [JobOfferStatus.EXPIRED, JobOfferStatus.PENDING]:
            raise SystemExit(f"unexpected offer statuses: {statuses}")

        carrier_ids = {offer.carrier_id for offer in offers}
        if next_carrier.id not in carrier_ids:
            raise SystemExit("next carrier did not receive redispatched offer")

        loaded_job = await job_repo.get_job_by_id(job.id)
        if loaded_job.status != JobStatus.OFFERED:
            raise SystemExit(f"unexpected job status: {loaded_job.status}")

        if bot.messages:
            raise SystemExit("did not expect admin escalation while redispatch succeeded")

        accepted_job = await job_repo.create_job(
            Job(
                client_telegram_user_id=9002,
                client_telegram_username="client_accepted",
                client_phone=None,
                client_whatsapp=None,
                status=JobStatus.OFFERED,
                requested_date=None,
                assigned_at=None,
                started_at=None,
                completed_at=None,
                cancelled_at=None,
                client_confirmation_status=None,
                carrier_confirmation_status=None,
                needs_assembly=False,
                needs_packing=False,
                needs_tail_lift=False,
                needs_crane=False,
                needs_mobile_lift=False,
                required_loaders=1,
                estimated_payload_kg=500,
                estimated_volume_m3=5.0,
                comment=None,
                created_at=now,
                updated_at=now,
            )
        )

        await job_repo.add_address(
            JobAddress(
                job_id=accepted_job.id,
                kind="pickup",
                raw_text="Lisboa",
                original_google_maps_url=None,
                normalized_address="Lisboa",
                city=None,
                postal_code=None,
                floor=None,
                has_elevator=None,
                latitude=None,
                longitude=None,
                map_url=None,
                created_at=now,
            )
        )

        await job_repo.create_offer(
            JobOffer(
                job_id=accepted_job.id,
                carrier_id=expired_carrier.id,
                vehicle_id=expired_vehicle.id,
                status=JobOfferStatus.ACCEPTED,
                offered_at=now - timedelta(hours=2),
                responded_at=now - timedelta(hours=1, minutes=30),
                expires_at=now - timedelta(hours=1),
                carrier_note=None,
                price_cents=None,
                carrier_message_chat_id=None,
                carrier_message_id=None,
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=1, minutes=30),
            )
        )

        await job_repo.create_offer(
            JobOffer(
                job_id=accepted_job.id,
                carrier_id=next_carrier.id,
                vehicle_id=expired_vehicle.id,
                status=JobOfferStatus.PENDING,
                offered_at=now - timedelta(hours=2),
                responded_at=None,
                expires_at=now - timedelta(hours=1),
                carrier_note=None,
                price_cents=None,
                carrier_message_chat_id=None,
                carrier_message_id=None,
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
            )
        )

        await session.commit()

        processed = await process_expired_pending_offers(
            bot=bot,
            session=session,
        )
        await session.commit()

        if processed != 1:
            raise SystemExit(f"expected 1 processed accepted-job offer, got {processed}")

        accepted_job_offers = await job_repo.list_offers_by_job(accepted_job.id)
        accepted_job_statuses = sorted(offer.status for offer in accepted_job_offers)

        if accepted_job_statuses != [JobOfferStatus.ACCEPTED, JobOfferStatus.EXPIRED]:
            raise SystemExit(
                f"unexpected accepted-job offer statuses: {accepted_job_statuses}"
            )

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "offer-expiry-runtime-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_offer_expiry())
    shutil.rmtree(DATA_DIR)

    print("OFFER_EXPIRY_RUNTIME_SMOKE_OK")


if __name__ == "__main__":
    main()
