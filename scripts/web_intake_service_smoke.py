import asyncio
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.job_status import JobStatus
from app.domain.requested_date import RequestedDateInPastError
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService

DATA_DIR = PROJECT_ROOT / ".tmp_web_intake_service_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_web_intake_service_smoke/cargopt_dev.db"


class FakeBot:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, *, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


async def exercise_web_intake() -> None:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        job_repository = JobRepository(session)
        carrier_repository = CarrierRepository(session)
        bot = FakeBot()
        service = RequestIntakeService(
            job_repository=job_repository,
            carrier_repository=carrier_repository,
            bot=bot,
        )

        request = RequestIntakeInput(
            source_locale="ru",
            customer_name="Web Client",
            customer_email="client@example.test",
            preferred_contact="whatsapp",
            client_phone="+351900000000",
            client_whatsapp="+351900000000",
            utm_source="landing",
            utm_medium="organic",
            utm_campaign="lisbon_launch",
            utm_content="hero_form",
            landing_version="v1",
            requested_date=datetime.now(UTC) + timedelta(days=30),
            addresses=(
                RequestIntakeAddress(
                    kind="pickup",
                    raw_text="Lisboa",
                    floor=2,
                    has_elevator=True,
                ),
                RequestIntakeAddress(
                    kind="dropoff",
                    raw_text="Porto",
                    floor=0,
                    has_elevator=False,
                ),
            ),
            items=(RequestIntakeItem(description="Boxes", quantity=10),),
            needs_tail_lift=False,
            estimated_payload_kg=500,
            estimated_volume_m3=3.0,
            comment="Submitted from web form",
        )

        past_request = replace(
            request,
            requested_date=datetime.now(UTC) - timedelta(days=2),
        )
        try:
            await service.submit_web_intake(past_request)
        except RequestedDateInPastError:
            pass
        else:
            raise AssertionError("past requested date must be rejected")

        result = await service.submit_web_intake(request)

        if result.job.id is None:
            raise SystemExit("web job id missing")

        loaded = await job_repository.get_job_by_id(result.job.id)
        if loaded is None:
            raise SystemExit("web job not loaded")

        if loaded.source != "web_form":
            raise SystemExit(f"unexpected source: {loaded.source}")
        if loaded.customer_name != "Web Client":
            raise SystemExit("customer name not stored")
        if loaded.utm_source != "landing":
            raise SystemExit("utm source not stored")
        if loaded.utm_medium != "organic":
            raise SystemExit("utm medium not stored")
        if loaded.utm_campaign != "lisbon_launch":
            raise SystemExit("utm campaign not stored")
        if loaded.utm_content != "hero_form":
            raise SystemExit("utm content not stored")

        addresses = await job_repository.list_addresses_by_job(loaded.id)
        if len(addresses) != 2:
            raise SystemExit(f"unexpected address count: {len(addresses)}")

        items = await job_repository.list_items_by_job(loaded.id)
        if len(items) != 1:
            raise SystemExit(f"unexpected item count: {len(items)}")

        if loaded.status != JobStatus.MANUAL_REVIEW_REQUIRED:
            raise SystemExit(f"unexpected final status without carriers: {loaded.status}")

        if result.offers_count != 0:
            raise SystemExit(f"unexpected offers count: {result.offers_count}")

        if not bot.messages:
            raise SystemExit("manual review admin notification was not sent")

        await session.commit()

    await engine.dispose()


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "web-intake-service-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()
    run([".venv/bin/alembic", "upgrade", "head"])
    asyncio.run(exercise_web_intake())
    shutil.rmtree(DATA_DIR)

    print("WEB_INTAKE_SERVICE_SMOKE_OK")


if __name__ == "__main__":
    main()
