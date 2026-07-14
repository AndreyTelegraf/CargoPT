import asyncio
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp_job_status_event_smoke"
DB = TMP / "cargopt.db"
URL = "sqlite+aiosqlite:///.tmp_job_status_event_smoke/cargopt.db"

os.environ["BOT_TOKEN"] = "123456:SMOKE"
os.environ["DATABASE_URL"] = URL
os.environ["ENVIRONMENT"] = "smoke"
os.environ["LOG_LEVEL"] = "INFO"
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.domain.job_status import JobStatus
from app.models.job import Job, JobStatusEvent
from app.repositories.job import JobRepository


def alembic(*args):
    subprocess.run(
        [".venv/bin/alembic", *args],
        cwd=ROOT,
        check=True,
        env=os.environ.copy(),
    )


async def exercise():
    engine = create_async_engine(URL)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    t0 = datetime(2026, 7, 14, 21, 15, tzinfo=UTC)

    async with sessions() as session:
        repo = JobRepository(session)

        job = await repo.create_job(
            Job(
                client_telegram_user_id=99001,
                client_telegram_username="status_event_smoke",
                status=JobStatus.DRAFT,
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
                required_loaders=None,
                estimated_payload_kg=None,
                estimated_volume_m3=None,
                comment=None,
                created_at=t0,
                updated_at=t0,
            )
        )

        await repo.update_comment_and_status(
            job.id,
            "submitted",
            JobStatus.READY_FOR_MATCHING,
            t0 + timedelta(minutes=1),
        )
        await repo.update_job_status(
            job.id,
            JobStatus.MATCHING,
            t0 + timedelta(minutes=2),
        )
        await repo.update_job_status(
            job.id,
            JobStatus.MATCHING,
            t0 + timedelta(minutes=3),
        )
        await session.commit()

        rows = (
            await session.execute(
                select(JobStatusEvent)
                .where(JobStatusEvent.job_id == job.id)
                .order_by(JobStatusEvent.id)
            )
        ).scalars().all()

        actual = [(x.from_status, x.to_status) for x in rows]
        expected = [
            (None, "draft"),
            ("draft", "ready_for_matching"),
            ("ready_for_matching", "matching"),
        ]

        assert actual == expected, actual

    await engine.dispose()


def exists():
    with sqlite3.connect(DB) as conn:
        return conn.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type='table' AND name='job_status_event'"
        ).fetchone() is not None


def main():
    shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir()

    alembic("upgrade", "head")
    assert exists()
    asyncio.run(exercise())

    alembic("downgrade", "20260714_1810_job_utm_medium_content")
    assert not exists()

    alembic("upgrade", "head")
    assert exists()

    shutil.rmtree(TMP)
    print("JOB_STATUS_EVENT_SMOKE_OK")


if __name__ == "__main__":
    main()
