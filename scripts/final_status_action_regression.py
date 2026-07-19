import asyncio
import os
import shutil
import subprocess
import sys
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = PROJECT_ROOT / ".tmp_final_status_action_regression"
DB_PATH = TMP_DIR / "cargopt.db"
DATABASE_URL = (
    "sqlite+aiosqlite:///"
    ".tmp_final_status_action_regression/cargopt.db"
)

os.environ["BOT_TOKEN"] = "123456:FINALREGRESSION"
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["ENVIRONMENT"] = "final-status-action-regression"
os.environ["LOG_LEVEL"] = "INFO"

sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
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
from app.models.job import JobStatusEvent
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.assignment_confirmation import (
    ASSIGNMENT_CONFIRMATION_CONFIRMED,
)
from app.services.assignment_confirmation import (
    ASSIGNMENT_CONFIRMATION_FAILED,
)
from app.services.assignment_confirmation import (
    process_assignment_failure_redispatch,
)
from app.services.assignment_confirmation import (
    record_assignment_confirmation,
)
from app.services.assignment_timeout import (
    process_stale_assignment_confirmations,
)
from app.services.job_lifecycle import cancel_job
from app.services.job_lifecycle import complete_job
from app.services.job_lifecycle import start_job
from app.services.job_offer import ClientOfferSelectionError
from app.services.job_offer import JobOfferService
from app.services.offer_expiry import process_expired_pending_offers


class FakeMessage:
    def __init__(self, *, chat_id: int, message_id: int) -> None:
        self.chat = SimpleNamespace(id=chat_id)
        self.message_id = message_id


class FakeBot:
    def __init__(self) -> None:
        self.sent_messages: list[dict] = []
        self.sent_photos: list[dict] = []
        self.sent_videos: list[dict] = []
        self.sent_media_groups: list[dict] = []
        self.deleted_messages: list[dict] = []
        self._message_id = 1000

    def _next_message(self, chat_id: int) -> FakeMessage:
        self._message_id += 1
        return FakeMessage(
            chat_id=chat_id,
            message_id=self._message_id,
        )

    async def send_message(self, *, chat_id, text, **kwargs):
        self.sent_messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "kwargs": kwargs,
            }
        )
        return self._next_message(chat_id)

    async def send_photo(self, *, chat_id, photo, **kwargs):
        self.sent_photos.append(
            {
                "chat_id": chat_id,
                "photo": photo,
                "kwargs": kwargs,
            }
        )
        return self._next_message(chat_id)

    async def send_video(self, *, chat_id, video, **kwargs):
        self.sent_videos.append(
            {
                "chat_id": chat_id,
                "video": video,
                "kwargs": kwargs,
            }
        )
        return self._next_message(chat_id)

    async def send_media_group(self, *, chat_id, media, **kwargs):
        self.sent_media_groups.append(
            {
                "chat_id": chat_id,
                "media": media,
                "kwargs": kwargs,
            }
        )
        return [
            self._next_message(chat_id)
            for _ in media
        ]

    async def delete_message(self, *, chat_id, message_id):
        self.deleted_messages.append(
            {
                "chat_id": chat_id,
                "message_id": message_id,
            }
        )


def run_alembic(*args: str) -> None:
    subprocess.run(
        [".venv/bin/alembic", *args],
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
        check=True,
    )


def reset_tmp() -> None:
    if TMP_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("regression must not target production data")

    shutil.rmtree(TMP_DIR, ignore_errors=True)
    TMP_DIR.mkdir()


async def create_carrier_with_vehicle(
    carrier_repository: CarrierRepository,
    *,
    name: str,
    telegram_user_id: int | None,
    now: datetime,
    operating_regions: str = "Lisboa",
):
    carrier = await carrier_repository.create_carrier(
        CarrierCompany(
            company_name=name,
            contact_name=f"{name} Contact",
            phone="+351900000000",
            telegram_user_id=telegram_user_id,
            telegram_username=name.lower().replace(" ", "_"),
            status=CarrierStatus.ACTIVE,
            paid_until=now + timedelta(days=30),
            assembly_required=False,
            packing_required=False,
            operating_regions=operating_regions,
            profile_completed_at=now,
            current_profile_step=None,
            internal_note=None,
            created_at=now,
            updated_at=now,
        )
    )

    vehicle = await carrier_repository.create_vehicle(
        CarrierVehicle(
            carrier_id=carrier.id,
            vehicle_type="large_van",
            payload_kg=2000,
            volume_m3=20.0,
            max_loaders=3,
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

    return carrier, vehicle


async def create_job(
    job_repository: JobRepository,
    *,
    now: datetime,
    status: JobStatus,
    client_id: int,
    username: str,
    assigned_at: datetime | None = None,
) -> Job:
    job = await job_repository.create_job(
        Job(
            client_telegram_user_id=client_id,
            client_telegram_username=username,
            source="regression",
            source_locale="ru",
            customer_name=username,
            customer_email=f"{username}@example.test",
            preferred_contact="telegram",
            client_phone="+351911111111",
            client_whatsapp="+351911111111",
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            utm_content=None,
            landing_version="final-regression",
            status=status,
            requested_date=now + timedelta(days=1),
            assigned_at=assigned_at,
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
            comment="final regression",
            created_at=now,
            updated_at=now,
        )
    )

    await job_repository.add_address(
        JobAddress(
            job_id=job.id,
            kind="pickup",
            raw_text="Lisboa",
            original_google_maps_url=None,
            normalized_address="Lisboa",
            city="Lisboa",
            postal_code=None,
            floor=None,
            has_elevator=None,
            latitude=None,
            longitude=None,
            map_url=None,
            created_at=now,
        )
    )

    return job


async def get_status_events(
    session,
    *,
    job_id: int,
) -> list[tuple[str | None, str]]:
    rows = (
        await session.execute(
            select(JobStatusEvent)
            .where(JobStatusEvent.job_id == job_id)
            .order_by(JobStatusEvent.id)
        )
    ).scalars().all()

    return [
        (row.from_status, row.to_status)
        for row in rows
    ]


async def assert_single_accepted_offer(
    job_repository: JobRepository,
    *,
    job_id: int,
) -> JobOffer:
    offers = await job_repository.list_offers_by_job(job_id)
    accepted = [
        offer
        for offer in offers
        if offer.status == JobOfferStatus.ACCEPTED
    ]

    if len(accepted) != 1:
        raise AssertionError(
            f"job {job_id}: expected one accepted offer, "
            f"got {[offer.status for offer in offers]}"
        )

    return accepted[0]


async def scenario_client_selection_and_confirmation(
    session,
    *,
    now: datetime,
) -> None:
    carrier_repository = CarrierRepository(session)
    job_repository = JobRepository(session)
    offer_service = JobOfferService(job_repository)

    _, first_vehicle = await create_carrier_with_vehicle(
        carrier_repository,
        name="Selected Carrier",
        telegram_user_id=7001,
        now=now,
    )
    _, second_vehicle = await create_carrier_with_vehicle(
        carrier_repository,
        name="Rejected Carrier",
        telegram_user_id=7002,
        now=now,
    )
    _, third_vehicle = await create_carrier_with_vehicle(
        carrier_repository,
        name="Pending Carrier",
        telegram_user_id=7003,
        now=now,
    )

    job = await create_job(
        job_repository,
        now=now,
        status=JobStatus.MATCHING,
        client_id=9001,
        username="selection_client",
    )

    first = await offer_service.create_offer(
        job_id=job.id,
        vehicle=first_vehicle,
    )
    second = await offer_service.create_offer(
        job_id=job.id,
        vehicle=second_vehicle,
    )
    third = await offer_service.create_offer(
        job_id=job.id,
        vehicle=third_vehicle,
    )

    await offer_service.accept_offer_without_assignment(first.id)
    await offer_service.accept_offer_without_assignment(second.id)

    offered_job = await job_repository.get_job_by_id(job.id)
    if offered_job.status != JobStatus.OFFERED:
        raise AssertionError(
            f"carrier acceptance changed job unexpectedly: "
            f"{offered_job.status}"
        )

    accepted_before_selection = [
        offer
        for offer in await job_repository.list_offers_by_job(job.id)
        if offer.status == JobOfferStatus.ACCEPTED
    ]
    if len(accepted_before_selection) != 2:
        raise AssertionError(
            "offered job must support multiple accepted carrier offers"
        )

    await offer_service.select_accepted_offer_for_client(
        job_id=job.id,
        offer_id=first.id,
    )

    selected_job = await job_repository.get_job_by_id(job.id)
    if selected_job.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
        raise AssertionError(
            f"unexpected selected job status: {selected_job.status}"
        )

    if selected_job.assigned_at is None:
        raise AssertionError("assigned_at missing after selection")

    selected_offer = await assert_single_accepted_offer(
        job_repository,
        job_id=job.id,
    )
    if selected_offer.id != first.id:
        raise AssertionError("wrong accepted offer remained selected")

    second_loaded = await job_repository.get_offer_by_id(second.id)
    third_loaded = await job_repository.get_offer_by_id(third.id)

    if second_loaded.status != JobOfferStatus.CANCELLED:
        raise AssertionError("unselected accepted offer was not cancelled")

    if third_loaded.status != JobOfferStatus.DECLINED:
        raise AssertionError("unselected pending offer was not declined")

    after_client = await record_assignment_confirmation(
        job_repository,
        job_id=job.id,
        actor="client",
        status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
    )

    if after_client.status != JobStatus.ASSIGNED_PENDING_CONFIRMATION:
        raise AssertionError("first confirmation finalized assignment")

    after_carrier = await record_assignment_confirmation(
        job_repository,
        job_id=job.id,
        actor="carrier",
        status=ASSIGNMENT_CONFIRMATION_CONFIRMED,
    )

    if after_carrier.status != JobStatus.ASSIGNED:
        raise AssertionError(
            f"both confirmations did not assign job: "
            f"{after_carrier.status}"
        )

    try:
        await offer_service.select_accepted_offer_for_client(
            job_id=job.id,
            offer_id=first.id,
        )
    except ClientOfferSelectionError:
        pass
    else:
        raise AssertionError("duplicate client selection succeeded")

    events = await get_status_events(
        session,
        job_id=job.id,
    )

    expected = [
        (None, JobStatus.MATCHING),
        (JobStatus.MATCHING, JobStatus.OFFERED),
        (
            JobStatus.OFFERED,
            JobStatus.ASSIGNED_PENDING_CONFIRMATION,
        ),
        (
            JobStatus.ASSIGNED_PENDING_CONFIRMATION,
            JobStatus.ASSIGNED,
        ),
    ]

    if events != expected:
        raise AssertionError(
            f"unexpected confirmation events: {events}"
        )


async def scenario_failure_and_redispatch(
    session,
    *,
    now: datetime,
) -> None:
    carrier_repository = CarrierRepository(session)
    job_repository = JobRepository(session)
    offer_service = JobOfferService(job_repository)
    bot = FakeBot()

    _, selected_vehicle = await create_carrier_with_vehicle(
        carrier_repository,
        name="Failure Selected Carrier",
        telegram_user_id=7101,
        now=now,
    )
    next_carrier, _ = await create_carrier_with_vehicle(
        carrier_repository,
        name="Failure Next Carrier",
        telegram_user_id=7102,
        now=now,
    )

    job = await create_job(
        job_repository,
        now=now,
        status=JobStatus.MATCHING,
        client_id=9101,
        username="failure_client",
    )

    offer = await offer_service.create_offer(
        job_id=job.id,
        vehicle=selected_vehicle,
    )
    await offer_service.accept_offer_and_assign_job(offer.id)

    failed_job = await record_assignment_confirmation(
        job_repository,
        job_id=job.id,
        actor="carrier",
        status=ASSIGNMENT_CONFIRMATION_FAILED,
    )

    if failed_job.status != JobStatus.READY_FOR_MATCHING:
        raise AssertionError(
            f"failure did not reopen search: {failed_job.status}"
        )

    cancelled_offer = await job_repository.get_offer_by_id(offer.id)
    if cancelled_offer.status != JobOfferStatus.CANCELLED:
        raise AssertionError("failed assignment offer not cancelled")

    await process_assignment_failure_redispatch(
        bot=bot,
        job=failed_job,
        accepted_offer=cancelled_offer,
        job_repository=job_repository,
        carrier_repository=carrier_repository,
    )

    redispatched_job = await job_repository.get_job_by_id(job.id)
    if redispatched_job.status != JobStatus.OFFERED:
        raise AssertionError(
            f"redispatch did not return offered: "
            f"{redispatched_job.status}"
        )

    offers = await job_repository.list_offers_by_job(job.id)
    pending = [
        item
        for item in offers
        if item.status == JobOfferStatus.PENDING
    ]

    if not 1 <= len(pending) <= 5:
        raise AssertionError(
            f"expected 1..5 redispatched offers: "
            f"{[item.status for item in offers]}"
        )

    pending_carrier_ids = [
        item.carrier_id
        for item in pending
    ]

    if selected_vehicle.carrier_id in pending_carrier_ids:
        raise AssertionError(
            "failed assignment carrier received a duplicate redispatch"
        )

    if len(pending_carrier_ids) != len(set(pending_carrier_ids)):
        raise AssertionError(
            f"duplicate redispatch carrier ids: {pending_carrier_ids}"
        )

    if len(bot.sent_messages) != len(pending):
        raise AssertionError(
            f"redispatch notification count mismatch: "
            f"messages={len(bot.sent_messages)} "
            f"pending={len(pending)}"
        )


async def scenario_assignment_timeout(
    session,
    *,
    now: datetime,
) -> None:
    carrier_repository = CarrierRepository(session)
    job_repository = JobRepository(session)
    offer_service = JobOfferService(job_repository)
    bot = FakeBot()

    selected_carrier, selected_vehicle = (
        await create_carrier_with_vehicle(
            carrier_repository,
            name="Timeout Selected Carrier",
            telegram_user_id=7201,
            now=now,
        )
    )
    next_carrier, _ = await create_carrier_with_vehicle(
        carrier_repository,
        name="Timeout Next Carrier",
        telegram_user_id=7202,
        now=now,
    )

    stale_assigned_at = now - timedelta(hours=25)

    job = await create_job(
        job_repository,
        now=now - timedelta(days=1),
        status=JobStatus.MATCHING,
        client_id=9201,
        username="timeout_client",
    )

    offer = await offer_service.create_offer(
        job_id=job.id,
        vehicle=selected_vehicle,
    )
    await offer_service.accept_offer_and_assign_job(offer.id)

    loaded = await job_repository.get_job_by_id(job.id)
    loaded.assigned_at = stale_assigned_at
    loaded.updated_at = stale_assigned_at
    await session.flush()

    processed = await process_stale_assignment_confirmations(
        bot=bot,
        session=session,
        timeout_hours=24,
    )

    if processed != 1:
        raise AssertionError(
            f"expected one assignment timeout, got {processed}"
        )

    timed_out = await job_repository.get_job_by_id(job.id)
    if timed_out.status != JobStatus.OFFERED:
        raise AssertionError(
            f"timeout redispatch status unexpected: {timed_out.status}"
        )

    offers = await job_repository.list_offers_by_job(job.id)
    cancelled = [
        item
        for item in offers
        if item.status == JobOfferStatus.CANCELLED
        and item.carrier_id == selected_carrier.id
    ]
    pending = [
        item
        for item in offers
        if item.status == JobOfferStatus.PENDING
    ]

    if len(cancelled) != 1:
        raise AssertionError(
            f"expected one cancelled selected offer: "
            f"{[(item.carrier_id, item.status) for item in offers]}"
        )

    if not 1 <= len(pending) <= 5:
        raise AssertionError(
            f"expected 1..5 timeout redispatch offers: "
            f"{[(item.carrier_id, item.status) for item in offers]}"
        )

    pending_carrier_ids = [
        item.carrier_id
        for item in pending
    ]

    if selected_carrier.id in pending_carrier_ids:
        raise AssertionError(
            "timed-out selected carrier received a duplicate redispatch"
        )

    if len(pending_carrier_ids) != len(set(pending_carrier_ids)):
        raise AssertionError(
            f"duplicate timeout redispatch carriers: "
            f"{pending_carrier_ids}"
        )

    messages_by_chat = {
        item["chat_id"]: item["text"]
        for item in bot.sent_messages
    }

    client_text = messages_by_chat.get(job.client_telegram_user_id, "")
    carrier_text = messages_by_chat.get(
        selected_carrier.telegram_user_id,
        "",
    )

    if "подтверждение не было получено вовремя" not in client_text:
        raise AssertionError("client timeout notification missing")

    if "Для вас эта заявка закрыта" not in carrier_text:
        raise AssertionError("carrier timeout notification missing")


async def scenario_offer_expiry(
    session,
    *,
    now: datetime,
) -> None:
    carrier_repository = CarrierRepository(session)
    job_repository = JobRepository(session)
    bot = FakeBot()

    expired_carrier, expired_vehicle = (
        await create_carrier_with_vehicle(
            carrier_repository,
            name="Expired Carrier",
            telegram_user_id=7301,
            now=now,
        )
    )
    next_carrier, _ = await create_carrier_with_vehicle(
        carrier_repository,
        name="Expiry Next Carrier",
        telegram_user_id=7302,
        now=now,
    )

    job = await create_job(
        job_repository,
        now=now,
        status=JobStatus.OFFERED,
        client_id=9301,
        username="expiry_client",
    )

    await job_repository.create_offer(
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

    processed = await process_expired_pending_offers(
        bot=bot,
        session=session,
    )

    if processed != 1:
        raise AssertionError(
            f"expected one expired offer, got {processed}"
        )

    loaded_job = await job_repository.get_job_by_id(job.id)
    if loaded_job.status != JobStatus.OFFERED:
        raise AssertionError(
            f"expiry redispatch status unexpected: "
            f"{loaded_job.status}"
        )

    offers = await job_repository.list_offers_by_job(job.id)
    expired = [
        item
        for item in offers
        if item.status == JobOfferStatus.EXPIRED
    ]
    pending = [
        item
        for item in offers
        if item.status == JobOfferStatus.PENDING
    ]

    if len(expired) != 1:
        raise AssertionError(
            f"expected one expired source offer: "
            f"{[(item.carrier_id, item.status) for item in offers]}"
        )

    if not 1 <= len(pending) <= 5:
        raise AssertionError(
            f"expected 1..5 expiry redispatch offers: "
            f"{[(item.carrier_id, item.status) for item in offers]}"
        )

    pending_carrier_ids = [
        item.carrier_id
        for item in pending
    ]

    if expired_carrier.id in pending_carrier_ids:
        raise AssertionError(
            "expired carrier received a duplicate redispatch"
        )

    if len(pending_carrier_ids) != len(set(pending_carrier_ids)):
        raise AssertionError(
            f"duplicate expiry redispatch carriers: "
            f"{pending_carrier_ids}"
        )


async def scenario_lifecycle_completion_and_cancel(
    session,
    *,
    now: datetime,
) -> None:
    job_repository = JobRepository(session)

    lifecycle_job = await create_job(
        job_repository,
        now=now,
        status=JobStatus.ASSIGNED,
        client_id=9401,
        username="lifecycle_client",
        assigned_at=now,
    )

    started = await start_job(
        job_repository,
        job_id=lifecycle_job.id,
    )
    if started.status != JobStatus.IN_PROGRESS:
        raise AssertionError("assigned job did not start")
    if started.started_at is None:
        raise AssertionError("started_at missing")

    completed = await complete_job(
        job_repository,
        job_id=lifecycle_job.id,
    )
    if completed.status != JobStatus.COMPLETED:
        raise AssertionError("in-progress job did not complete")
    if completed.completed_at is None:
        raise AssertionError("completed_at missing")

    cancel_job_record = await create_job(
        job_repository,
        now=now,
        status=JobStatus.READY_FOR_MATCHING,
        client_id=9402,
        username="cancel_client",
    )

    cancelled = await cancel_job(
        job_repository,
        job_id=cancel_job_record.id,
    )
    if cancelled.status != JobStatus.CANCELLED:
        raise AssertionError("job did not cancel")
    if cancelled.cancelled_at is None:
        raise AssertionError("cancelled_at missing")

    cancelled_from = await job_repository.get_cancelled_from_status(
        cancel_job_record.id,
    )
    if cancelled_from != JobStatus.READY_FOR_MATCHING:
        raise AssertionError(
            f"unexpected cancelled_from_status: {cancelled_from}"
        )


async def assert_database_contracts(session) -> None:
    jobs = (
        await session.execute(
            select(Job).order_by(Job.id)
        )
    ).scalars().all()

    for job in jobs:
        offers = (
            await session.execute(
                select(JobOffer)
                .where(JobOffer.job_id == job.id)
                .order_by(JobOffer.id)
            )
        ).scalars().all()

        accepted_count = sum(
            item.status == JobOfferStatus.ACCEPTED
            for item in offers
        )
        pending_count = sum(
            item.status == JobOfferStatus.PENDING
            for item in offers
        )

        if job.status in {
            JobStatus.ASSIGNED_PENDING_CONFIRMATION,
            JobStatus.ASSIGNED,
            JobStatus.IN_PROGRESS,
        } and accepted_count != 1:
            raise AssertionError(
                f"job {job.id} status {job.status}: "
                f"accepted_count={accepted_count}"
            )

        if job.status in {
            JobStatus.DRAFT,
            JobStatus.READY_FOR_MATCHING,
            JobStatus.MATCHING,
            JobStatus.NO_CARRIERS_FOUND,
            JobStatus.OFFERS_EXHAUSTED,
            JobStatus.EXPIRED_WITHOUT_RESPONSE,
            JobStatus.MANUAL_REVIEW_REQUIRED,
            JobStatus.CANCELLED,
        } and accepted_count != 0:
            raise AssertionError(
                f"job {job.id} status {job.status} "
                f"retains accepted offers"
            )

        if job.status in {
            JobStatus.CANCELLED,
            JobStatus.COMPLETED,
        } and pending_count != 0:
            raise AssertionError(
                f"final job {job.id} retains pending offers"
            )

        active_by_carrier: dict[int, int] = {}

        for offer in offers:
            if offer.status not in {
                JobOfferStatus.PENDING,
                JobOfferStatus.ACCEPTED,
            }:
                continue

            active_by_carrier[offer.carrier_id] = (
                active_by_carrier.get(offer.carrier_id, 0) + 1
            )

        duplicates = {
            carrier_id: count
            for carrier_id, count in active_by_carrier.items()
            if count > 1
        }

        if duplicates:
            raise AssertionError(
                f"job {job.id} has duplicate active offers: "
                f"{duplicates}"
            )


async def exercise() -> None:
    engine = create_async_engine(DATABASE_URL)
    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    now = datetime.now(UTC)

    try:
        async with sessions() as session:
            await scenario_client_selection_and_confirmation(
                session,
                now=now,
            )
            await session.commit()

            await scenario_failure_and_redispatch(
                session,
                now=now + timedelta(minutes=10),
            )
            await session.commit()

            await scenario_assignment_timeout(
                session,
                now=now + timedelta(minutes=20),
            )
            await session.commit()

            await scenario_offer_expiry(
                session,
                now=now + timedelta(minutes=30),
            )
            await session.commit()

            await scenario_lifecycle_completion_and_cancel(
                session,
                now=now + timedelta(minutes=40),
            )
            await session.commit()

            await assert_database_contracts(session)
    finally:
        await engine.dispose()


def main() -> None:
    reset_tmp()

    try:
        run_alembic("upgrade", "head")
        asyncio.run(exercise())
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)

    print("FINAL_STATUS_ACTION_REGRESSION_OK")


if __name__ == "__main__":
    main()
