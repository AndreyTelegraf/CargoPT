import asyncio
import os
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp_cancelled_stage_smoke"
DB_URL = (
    "sqlite+aiosqlite:///"
    ".tmp_cancelled_stage_smoke/cargopt.db"
)

os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = DB_URL
os.environ["ENVIRONMENT"] = "cancelled-stage-smoke"
os.environ["LOG_LEVEL"] = "INFO"

sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.job import Job
from app.repositories.job import JobRepository


def run(command: list[str]) -> None:
    subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        env=os.environ.copy(),
    )


def make_job(
    user_id: int,
    now: datetime,
    *,
    status: str = "draft",
    assigned_at=None,
    started_at=None,
    cancelled_at=None,
) -> Job:
    return Job(
        client_telegram_user_id=user_id,
        client_telegram_username=f"cancel_stage_{user_id}",
        client_phone=None,
        client_whatsapp=None,
        source="smoke",
        source_locale="pt",
        customer_name="Smoke",
        customer_email=None,
        preferred_contact=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        landing_version=None,
        status=status,
        requested_date=None,
        assigned_at=assigned_at,
        started_at=started_at,
        completed_at=None,
        cancelled_at=cancelled_at,
        client_confirmation_status=None,
        carrier_confirmation_status=None,
        needs_assembly=False,
        needs_packing=False,
        needs_tail_lift=False,
        needs_crane=False,
        needs_mobile_lift=False,
        required_loaders=None,
        estimated_payload_kg=None,
        estimated_volume_m3=None,
        comment=None,
        created_at=now,
        updated_at=now,
    )


async def exercise() -> None:
    engine = create_async_engine(DB_URL)
    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    now = datetime.now(UTC)

    async with sessions() as session:
        repository = JobRepository(session)

        statuses = (
            "draft",
            "ready_for_matching",
            "matching",
            "offered",
            "assigned_pending_confirmation",
            "assigned",
            "in_progress",
        )

        for offset, expected in enumerate(
            statuses,
            start=1,
        ):
            job = await repository.create_job(
                make_job(
                    98000 + offset,
                    now,
                )
            )

            if expected != "draft":
                await repository.update_job_status(
                    job_id=job.id,
                    status=expected,
                    updated_at=(
                        now
                        + timedelta(minutes=offset)
                    ),
                )

            await repository.update_job_status(
                job_id=job.id,
                status="cancelled",
                updated_at=(
                    now
                    + timedelta(
                        minutes=offset + 20,
                    )
                ),
            )

            actual = (
                await repository
                .get_cancelled_from_status(job.id)
            )

            assert actual == expected, (
                expected,
                actual,
            )

        legacy_assigned = await repository.create_job(
            make_job(
                98901,
                now,
                status="cancelled",
                assigned_at=now,
                cancelled_at=now,
            )
        )

        assert (
            await repository
            .get_cancelled_from_status(
                legacy_assigned.id
            )
        ) == "assigned"

        legacy_started = await repository.create_job(
            make_job(
                98902,
                now,
                status="cancelled",
                assigned_at=now,
                started_at=now,
                cancelled_at=now,
            )
        )

        assert (
            await repository
            .get_cancelled_from_status(
                legacy_started.id
            )
        ) == "in_progress"

        legacy_unknown = await repository.create_job(
            make_job(
                98903,
                now,
                status="cancelled",
                cancelled_at=now,
            )
        )

        assert (
            await repository
            .get_cancelled_from_status(
                legacy_unknown.id
            )
        ) is None

        await session.commit()

    await engine.dispose()


def main() -> None:
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir()

    try:
        run([
            ".venv/bin/alembic",
            "upgrade",
            "head",
        ])

        asyncio.run(exercise())
    finally:
        shutil.rmtree(
            TMP,
            ignore_errors=True,
        )

    print("CANCELLED_STAGE_REPOSITORY_SMOKE_OK")
    print("CANCELLED_STAGE_LEGACY_FALLBACK_OK")


if __name__ == "__main__":
    main()
