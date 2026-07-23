import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.repositories.carrier import CarrierRepository
from app.services.carrier_onboarding import CarrierOnboardingService


DATA_DIR = PROJECT_ROOT / ".tmp_carrier_onboarding_service_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_carrier_onboarding_service_smoke/cargopt_dev.db"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def exercise_service() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        repository = CarrierRepository(session)
        service = CarrierOnboardingService(repository)

        carrier = await service.create_draft_carrier(
            company_name="Service Smoke Carrier",
            contact_name="Service Contact",
            phone="+351900000002",
            internal_note="service smoke",
        )

        if carrier.id is None:
            raise SystemExit("carrier id was not assigned")
        if carrier.status != "draft":
            raise SystemExit(f"unexpected carrier status: {carrier.status}")

        invite = await service.create_invite_token(
            carrier_id=carrier.id,
            created_by_admin_id=1001,
            expires_in_days=7,
        )

        if not invite.token:
            raise SystemExit("invite token is empty")
        if invite.status != "active":
            raise SystemExit(f"unexpected invite status: {invite.status}")

        if carrier.status != "invited":
            raise SystemExit(
                f"carrier status should be invited, got {carrier.status}"
            )

        validated = await service.validate_invite_token(invite.token)

        if validated.token != invite.token:
            raise SystemExit("validated token mismatch")

        await session.commit()

        loaded_invite = await service.get_invite_token(invite.token)
        if loaded_invite is None:
            raise SystemExit("loaded invite missing")
        if loaded_invite.carrier_id != carrier.id:
            raise SystemExit("loaded invite carrier mismatch")

        claimed = await service.claim_invite_token(
            token=invite.token,
            telegram_user_id=555000111,
        )

        if claimed.status != "used":
            raise SystemExit("invite should be used")

        active_carrier = await repository.get_carrier_by_id(carrier.id)

        if active_carrier is None:
            raise SystemExit("carrier missing after claim")

        if active_carrier.status != "invited":
            raise SystemExit(
                f"carrier should remain invited after claim, got {active_carrier.status}"
            )

        if active_carrier.telegram_user_id != 555000111:
            raise SystemExit("telegram id mismatch")

        completed = await service.complete_profile(
            carrier_id=carrier.id,
            assembly_required=True,
            packing_required=True,
            operating_regions="Lisboa, Setubal",
        )

        if completed.status != "pending_moderation":
            raise SystemExit(
                f"completed profile should await moderation, got {completed.status}"
            )

        if completed.profile_completed_at is None:
            raise SystemExit("profile_completed_at missing")

        if completed.operating_regions != "Lisboa, Setubal":
            raise SystemExit("operating_regions mismatch")


    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "carrier-onboarding-service-smoke-token"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "carrier-onboarding-service-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])

    asyncio.run(exercise_service())

    shutil.rmtree(DATA_DIR)

    print("CARRIER_ONBOARDING_SERVICE_SMOKE_OK")



if __name__ == "__main__":
    main()
