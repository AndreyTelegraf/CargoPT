import asyncio
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///data/cargopt_dev.db")

from app.bot.handlers.dispatcher_jobs_admin import (  # noqa: E402
    MANUAL_DISPATCH_PAGE_SIZE,
    _build_manual_dispatch_keyboard,
)
from app.db.base import Base  # noqa: E402
from app.models.carrier import CarrierCompany, CarrierVehicle  # noqa: E402
from app.models.job import Job, JobAddress, JobOffer  # noqa: E402
from app.repositories.carrier import CarrierRepository  # noqa: E402
from app.repositories.job import JobRepository  # noqa: E402


def make_carrier(
    carrier_id: int,
    *,
    now: datetime,
    status: str = "active",
    telegram: bool = True,
    subscription: bool = True,
    regions: str = "Lisboa",
) -> CarrierCompany:
    return CarrierCompany(
        id=carrier_id,
        company_name=f"@carrier{carrier_id:02}",
        telegram_user_id=1000 + carrier_id if telegram else None,
        telegram_username=f"carrier{carrier_id:02}" if telegram else None,
        status=status,
        paid_until=now + timedelta(days=30) if subscription else None,
        assembly_required=True,
        packing_required=True,
        operating_regions=regions,
        created_at=now,
        updated_at=now,
    )


def make_vehicle(carrier_id: int, *, now: datetime) -> CarrierVehicle:
    return CarrierVehicle(
        id=carrier_id,
        carrier_id=carrier_id,
        vehicle_type="Van",
        payload_kg=1200,
        volume_m3=15.0,
        max_loaders=2,
        has_tail_lift=False,
        has_crane=False,
        has_mobile_lift=False,
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def make_offer(carrier_id: int, status: str, *, now: datetime) -> JobOffer:
    return JobOffer(
        job_id=138,
        carrier_id=carrier_id,
        vehicle_id=carrier_id,
        status=status,
        offered_at=now,
        responded_at=None if status == "pending" else now,
        expires_at=now + timedelta(hours=1),
        carrier_note=None,
        decline_reason=None,
        price_cents=None,
        carrier_message_chat_id=None,
        carrier_message_id=None,
        created_at=now,
        updated_at=now,
    )


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        job = Job(
            id=138,
            status="offered",
            needs_assembly=False,
            needs_packing=False,
            needs_tail_lift=False,
            needs_crane=False,
            needs_mobile_lift=False,
            required_loaders=None,
            estimated_payload_kg=None,
            estimated_volume_m3=None,
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.add(
            JobAddress(
                job_id=138,
                kind="pickup",
                raw_text="Lisboa",
                latitude=38.72,
                longitude=-9.14,
                created_at=now,
            )
        )

        for carrier_id in range(1, 14):
            options = {}
            if carrier_id == 6:
                options["regions"] = "Porto"
            elif carrier_id == 7:
                options["status"] = "invited"
            elif carrier_id == 9:
                options["telegram"] = False
            elif carrier_id == 10:
                options["subscription"] = False
            session.add(make_carrier(carrier_id, now=now, **options))
            if carrier_id not in {7, 8}:
                session.add(make_vehicle(carrier_id, now=now))

        for carrier_id, status in (
            (1, "pending"),
            (2, "accepted"),
            (3, "expired"),
            (4, "declined"),
            (5, "cancelled"),
        ):
            session.add(make_offer(carrier_id, status, now=now))
        await session.commit()

        jobs = JobRepository(session)
        carriers = CarrierRepository(session)
        all_carrier_ids = await jobs.list_offer_carrier_ids_by_job(138)
        active_carrier_ids = await jobs.list_active_offer_carrier_ids_by_job(138)
        assert all_carrier_ids == {1, 2, 3, 4, 5}
        assert active_carrier_ids == {1, 2}
        assert len(await carriers.list_all_carriers()) == 13
        assert len(await carriers.list_all_vehicles()) == 11

        page_one, page, total_pages, total_entries = await _build_manual_dispatch_keyboard(
            job=job,
            job_repository=jobs,
            carrier_repository=carriers,
            page=0,
        )
        assert MANUAL_DISPATCH_PAGE_SIZE == 10
        assert (page, total_pages, total_entries) == (0, 2, 13)
        assert page_one.inline_keyboard[-2][-1].callback_data == "job:138:manual:1"

        page_two, page, total_pages, total_entries = await _build_manual_dispatch_keyboard(
            job=job,
            job_repository=jobs,
            carrier_repository=carriers,
            page=1,
        )
        assert (page, total_pages, total_entries) == (1, 2, 13)
        assert page_two.inline_keyboard[-2][0].callback_data == "job:138:manual:0"

        entry_buttons = [
            row[0]
            for keyboard in (page_one, page_two)
            for row in keyboard.inline_keyboard[:-2]
        ]
        assert len(entry_buttons) == 13
        buttons = {button.text: button.callback_data for button in entry_buttons}
        assert any("[вне фильтра] @carrier06" in text for text in buttons)
        assert any("[оффер ожидает] @carrier01" in text for text in buttons)
        assert any("[оффер принят] @carrier02" in text for text in buttons)
        assert any("[invited] @carrier07" in text for text in buttons)
        assert any("[нет машины] @carrier08" in text for text in buttons)
        assert any("[нет Telegram] @carrier09" in text for text in buttons)
        assert any("[нет подписки] @carrier10" in text for text in buttons)

        for terminal_carrier_id in (3, 4, 5):
            callback = next(
                callback_data
                for text, callback_data in buttons.items()
                if f"@carrier{terminal_carrier_id:02}" in text
            )
            assert callback == f"job:138:send:{terminal_carrier_id}"

        for blocked_carrier_id in (1, 2, 7, 8, 9, 10):
            callback = next(
                callback_data
                for text, callback_data in buttons.items()
                if f"@carrier{blocked_carrier_id:02}" in text
            )
            assert callback == "job:138:noop"

        search_keyboard, page, total_pages, total_entries = (
            await _build_manual_dispatch_keyboard(
                job=job,
                job_repository=jobs,
                carrier_repository=carriers,
                carrier_query="@carrier13",
            )
        )
        assert (page, total_pages, total_entries) == (0, 1, 1)
        assert "@carrier13" in search_keyboard.inline_keyboard[0][0].text

    await engine.dispose()
    print("MANUAL_OFFER_REDISPATCH_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
