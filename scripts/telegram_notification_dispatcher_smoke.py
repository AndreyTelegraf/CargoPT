import asyncio
import json
import os
import sys
import tempfile
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///data/cargopt_dev.db"
os.environ["ENVIRONMENT"] = "telegram-notification-dispatcher-smoke"

import app.models  # noqa: F401, E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.models.job import Job  # noqa: E402
from app.models.job import JobOffer  # noqa: E402
from app.models.telegram_notification import TelegramNotificationOutbox  # noqa: E402
from app.services.telegram_dispatcher import TelegramNotificationDispatcher  # noqa: E402


class FakeBot:
    def __init__(self, *, fail_on_call: int | None = None) -> None:
        self.fail_on_call = fail_on_call
        self.calls = []
        self.message_ids = {}

    async def send_message(self, *, chat_id, text, **kwargs):
        self.calls.append((chat_id, text, kwargs))
        if len(self.calls) == self.fail_on_call:
            raise RuntimeError(f"simulated Telegram failure at call {self.fail_on_call}")
        message_id = 9000 + len(self.calls)
        self.message_ids[chat_id] = message_id
        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            message_id=message_id,
        )


def make_job(now: datetime, sequence: int) -> Job:
    return Job(
        tracking_token=f"dispatcher-smoke-{sequence}",
        status="ready_for_matching",
        short_lead_time_filtered=False,
        needs_assembly=False,
        needs_packing=False,
        needs_tail_lift=False,
        needs_crane=False,
        needs_mobile_lift=False,
        created_at=now,
        updated_at=now,
    )


def make_notification(
    *,
    job_id: int,
    recipient: int,
    sequence: int,
    now: datetime,
    offer_id: int | None = None,
    status: str = "pending",
    attempt_count: int = 0,
    last_attempt_at: datetime | None = None,
) -> TelegramNotificationOutbox:
    notification_type = "carrier_offer" if offer_id is not None else "manual_review"
    return TelegramNotificationOutbox(
        job_id=job_id,
        offer_id=offer_id,
        notification_type=notification_type,
        recipient_chat_id=recipient,
        dedupe_key=f"dispatcher-smoke:{sequence}",
        payload_json=json.dumps({"text": f"notification {sequence}"}),
        delivery_status=status,
        attempt_count=attempt_count,
        next_attempt_at=now if status in {"pending", "retry"} else None,
        last_attempt_at=last_attempt_at,
        sent_at=None,
        provider_chat_id=None,
        provider_message_id=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


async def rows(session_maker):
    async with session_maker() as session:
        return list(
            (
                await session.execute(
                    select(TelegramNotificationOutbox).order_by(
                        TelegramNotificationOutbox.id
                    )
                )
            ).scalars()
        )


async def exercise_failure_position(fail_on_call: int) -> None:
    with tempfile.TemporaryDirectory(prefix="cargopt-telegram-dispatch-") as temporary:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{Path(temporary) / 'dispatcher.db'}"
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        now = datetime.now(UTC)
        async with session_maker() as session:
            for sequence in range(1, 4):
                job = make_job(now, sequence)
                session.add(job)
                await session.flush()
                session.add(
                    make_notification(
                        job_id=job.id,
                        recipient=7000 + sequence,
                        sequence=sequence,
                        now=now,
                    )
                )
            await session.commit()

        failing_bot = FakeBot(fail_on_call=fail_on_call)
        dispatcher = TelegramNotificationDispatcher(
            session_maker=session_maker,
            bot=failing_bot,
            retry_base_seconds=0,
        )
        if await dispatcher.dispatch_due() != 3:
            raise AssertionError("one recipient failure stopped the batch")
        first_pass = await rows(session_maker)
        if [row.delivery_status for row in first_pass].count("retry") != 1:
            raise AssertionError("temporary failure was not persisted for retry")
        if [row.delivery_status for row in first_pass].count("sent") != 2:
            raise AssertionError("successful recipients were not persisted")
        if len(failing_bot.calls) != 3:
            raise AssertionError("dispatcher did not continue after recipient failure")

        retry_bot = FakeBot()
        restarted_dispatcher = TelegramNotificationDispatcher(
            session_maker=session_maker,
            bot=retry_bot,
            retry_base_seconds=0,
        )
        if await restarted_dispatcher.dispatch_due() != 1:
            raise AssertionError("restart did not process the persisted retry")
        if any(row.delivery_status != "sent" for row in await rows(session_maker)):
            raise AssertionError("retry did not reach sent state")
        if await restarted_dispatcher.dispatch_due() != 0:
            raise AssertionError("sent notifications were delivered twice")
        if len(retry_bot.calls) != 1:
            raise AssertionError("repeat handler duplicated a business action")
        await engine.dispose()


async def exercise_stale_recovery_and_offer_reference() -> None:
    with tempfile.TemporaryDirectory(prefix="cargopt-telegram-recovery-") as temporary:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{Path(temporary) / 'recovery.db'}"
        )
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        now = datetime.now(UTC)
        async with session_maker() as session:
            stale_job = make_job(now, 10)
            carrier_job = make_job(now, 11)
            carrier_job.status = "offered"
            session.add_all((stale_job, carrier_job))
            await session.flush()
            offer = JobOffer(
                job_id=carrier_job.id,
                carrier_id=1,
                vehicle_id=1,
                status="pending",
                offered_at=now,
                responded_at=None,
                expires_at=now + timedelta(hours=1),
                carrier_note=None,
                decline_reason=None,
                price_cents=None,
                carrier_message_chat_id=None,
                carrier_message_id=None,
                created_at=now,
                updated_at=now,
            )
            session.add(offer)
            await session.flush()
            session.add_all(
                (
                    make_notification(
                        job_id=stale_job.id,
                        recipient=7101,
                        sequence=10,
                        now=now,
                        status="sending",
                        attempt_count=1,
                        last_attempt_at=now - timedelta(minutes=10),
                    ),
                    make_notification(
                        job_id=carrier_job.id,
                        recipient=7102,
                        sequence=11,
                        now=now,
                        offer_id=offer.id,
                    ),
                )
            )
            await session.commit()

        bot = FakeBot()
        dispatcher = TelegramNotificationDispatcher(
            session_maker=session_maker,
            bot=bot,
            stale_sending_seconds=300,
        )
        if await dispatcher.dispatch_due() != 1:
            raise AssertionError("ambiguous sending claim must not be replayed")
        recovered = await rows(session_maker)
        if [row.delivery_status for row in recovered] != ["uncertain", "sent"]:
            raise AssertionError("interrupted delivery was not quarantined")
        if recovered[0].attempt_count != 1:
            raise AssertionError("quarantine must not add a delivery attempt")

        async with session_maker() as session:
            stored_offer = await session.get(JobOffer, offer.id)
            if (
                stored_offer.carrier_message_chat_id,
                stored_offer.carrier_message_id,
            ) != (7102, bot.message_ids[7102]):
                raise AssertionError("carrier offer message reference was not persisted")
        await engine.dispose()


async def main() -> None:
    for failure_position in (1, 2, 3):
        await exercise_failure_position(failure_position)
    await exercise_stale_recovery_and_offer_reference()
    print("TELEGRAM_NOTIFICATION_DISPATCHER_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
