import asyncio
from datetime import UTC
from datetime import datetime
import os
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / ".tmp_carrier_profile_identity_bind"
DATABASE_URL = (
    "sqlite+aiosqlite:///.tmp_carrier_profile_identity_bind/cargopt.db"
)

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = DATABASE_URL
sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.carrier_status import CarrierStatus
from app.models.carrier import CarrierCompany
from app.repositories.carrier import CarrierRepository


async def exercise() -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with sessions() as session:
        repository = CarrierRepository(session)
        carrier = await repository.create_carrier(
            CarrierCompany(
                company_name="@Telg_Skok",
                contact_name=None,
                phone=None,
                telegram_user_id=None,
                telegram_username="Telg_Skok",
                status=CarrierStatus.ACTIVE,
                paid_until=None,
                assembly_required=False,
                packing_required=False,
                operating_regions="Lisboa",
                profile_completed_at=now,
                current_profile_step="completed",
                internal_note=None,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

        found = await repository.get_carrier_by_username("@telg_skok")
        assert found is not None
        assert found.id == carrier.id

        bound = await repository.bind_carrier_telegram_identity(
            carrier.id,
            telegram_user_id=987654321,
            telegram_username="Telg_Skok",
        )
        await session.commit()
        assert bound.telegram_user_id == 987654321

        try:
            await repository.bind_carrier_telegram_identity(
                carrier.id,
                telegram_user_id=123,
                telegram_username="Telg_Skok",
            )
        except ValueError as exc:
            assert "already bound" in str(exc)
        else:
            raise AssertionError("rebinding guard did not reject another user")

    await engine.dispose()


def main() -> None:
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir()
    try:
        subprocess.run(
            [str(ROOT / ".venv/bin/alembic"), "upgrade", "head"],
            cwd=ROOT,
            env=os.environ.copy(),
            check=True,
        )
        asyncio.run(exercise())
    finally:
        shutil.rmtree(TMP_DIR)
    print("CARRIER_PROFILE_IDENTITY_BIND_OK")


if __name__ == "__main__":
    main()
