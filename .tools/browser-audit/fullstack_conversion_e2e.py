from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()
TMP_ARGUMENT = sys.argv[2]

if TMP_ARGUMENT != ".tmp_fullstack_conversion_e2e":
    raise RuntimeError(
        "temporary directory must be exactly "
        "'.tmp_fullstack_conversion_e2e'"
    )

TMP = PROJECT_ROOT / TMP_ARGUMENT

if TMP.is_symlink():
    raise RuntimeError("temporary directory must not be a symbolic link")

TMP = TMP.resolve()
PORT = int(sys.argv[3])

if (
    TMP.parent != PROJECT_ROOT
    or TMP.name != ".tmp_fullstack_conversion_e2e"
):
    raise RuntimeError("temporary directory escaped project root")

if TMP.exists():
    shutil.rmtree(TMP)

TMP.mkdir(parents=True)
OUT.mkdir(parents=True, exist_ok=True)

DATABASE_FILE = TMP / "cargopt_e2e.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILE}"

os.environ["BOT_TOKEN"] = "123456:FULLSTACK_E2E_ONLY"
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["ENVIRONMENT"] = "fullstack-conversion-e2e"
os.environ["LOG_LEVEL"] = "INFO"

sys.path.insert(0, str(PROJECT_ROOT))

from playwright.async_api import async_playwright
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
import uvicorn

import app.models  # noqa: F401
from app.api.main import app
from app.api.web_requests import get_api_bot
from app.db.base import Base
from app.domain.carrier_status import CarrierStatus
from app.domain.job_offer_status import JobOfferStatus
from app.domain.job_status import JobStatus
from app.models.carrier import CarrierCompany, CarrierVehicle
from app.models.job import Job, JobOffer
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.job_offer import JobOfferService
import app.services.job_matching as job_matching_module


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.next_message_id = 1000

    async def send_message(self, *, chat_id, text, **kwargs):
        self.next_message_id += 1

        safe_kwargs = {
            key: (
                value.model_dump(mode="json")
                if hasattr(value, "model_dump")
                else str(value)
            )
            for key, value in kwargs.items()
        }

        self.messages.append(
            {
                "method": "send_message",
                "chat_id": chat_id,
                "text": text,
                "kwargs": safe_kwargs,
            }
        )

        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            message_id=self.next_message_id,
        )

    async def send_photo(self, *, chat_id, photo, **kwargs):
        return await self.send_message(
            chat_id=chat_id,
            text=kwargs.get("caption") or "",
            photo=photo,
            **kwargs,
        )

    async def send_video(self, *, chat_id, video, **kwargs):
        return await self.send_message(
            chat_id=chat_id,
            text=kwargs.get("caption") or "",
            video=video,
            **kwargs,
        )

    async def send_media_group(self, *, chat_id, media, **kwargs):
        self.messages.append(
            {
                "method": "send_media_group",
                "chat_id": chat_id,
                "media_count": len(media),
                "kwargs": kwargs,
            }
        )
        return []


fake_bot = FakeBot()


class FakeAssignmentCallbackMessage:
    def __init__(self) -> None:
        self.text = "Подтвердите, состоялась ли сделка."
        self.caption = None
        self.edits: list[dict] = []

    async def edit_text(self, text, **kwargs):
        self.text = text
        self.edits.append(
            {
                "method": "edit_text",
                "text": text,
                "kwargs": {
                    key: (
                        value.model_dump(mode="json")
                        if hasattr(value, "model_dump")
                        else value
                    )
                    for key, value in kwargs.items()
                },
            }
        )
        return self

    async def edit_reply_markup(self, **kwargs):
        self.edits.append(
            {
                "method": "edit_reply_markup",
                "kwargs": {
                    key: (
                        value.model_dump(mode="json")
                        if hasattr(value, "model_dump")
                        else value
                    )
                    for key, value in kwargs.items()
                },
            }
        )
        return self


class FakeAssignmentCallback:
    def __init__(
        self,
        *,
        job_id: int,
        telegram_user_id: int,
    ) -> None:
        self.data = f"assignment:confirm:{job_id}"
        self.from_user = SimpleNamespace(
            id=telegram_user_id,
        )
        self.bot = fake_bot
        self.message = FakeAssignmentCallbackMessage()
        self.answers: list[dict] = []

    async def answer(self, text=None, **kwargs):
        self.answers.append(
            {
                "text": text,
                "kwargs": kwargs,
            }
        )
        return True


async def confirm_carrier_assignment(job_id: int) -> dict:
    from app.bot.handlers.job_assignment_confirmation import (
        handle_assignment_confirmation,
    )

    carrier_chat_ids = [
        int(message["chat_id"])
        for message in fake_bot.messages
        if (
            message.get("method") == "send_message"
            and message.get("chat_id") is not None
        )
    ]

    if not carrier_chat_ids:
        raise AssertionError(
            "carrier Telegram chat id was not captured"
        )

    callback = FakeAssignmentCallback(
        job_id=job_id,
        telegram_user_id=carrier_chat_ids[-1],
    )

    bot_message_count_before = len(fake_bot.messages)

    await handle_assignment_confirmation(callback)

    if not callback.answers:
        raise AssertionError(
            "carrier callback answer was not recorded"
        )

    if not callback.message.edits:
        raise AssertionError(
            "carrier callback message was not edited"
        )

    return {
        "telegram_user_id": callback.from_user.id,
        "answers": callback.answers,
        "message_edits": callback.message.edits,
        "new_bot_messages": (
            len(fake_bot.messages)
            - bot_message_count_before
        ),
    }


async def override_bot():
    yield fake_bot


app.dependency_overrides[get_api_bot] = override_bot


async def deterministic_geocode(_value: str):
    return 38.7223, -9.1393


job_matching_module.geocode_text_address = deterministic_geocode


async def create_schema_and_carrier() -> tuple[int, int]:
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async with session_maker() as session:
        repository = CarrierRepository(session)

        carrier = await repository.create_carrier(
            CarrierCompany(
                company_name="CargoPT Fullstack Carrier",
                contact_name="Transportador E2E",
                phone="+351920000000",
                telegram_user_id=880001,
                telegram_username="cargopt_e2e_carrier",
                status=CarrierStatus.ACTIVE,
                paid_until=now + timedelta(days=30),
                assembly_required=False,
                packing_required=False,
                operating_regions="Lisboa",
                profile_completed_at=now,
                current_profile_step=None,
                internal_note="isolated fullstack e2e",
                created_at=now,
                updated_at=now,
            )
        )

        vehicle = await repository.create_vehicle(
            CarrierVehicle(
                carrier_id=carrier.id,
                vehicle_type="large_van",
                payload_kg=2000,
                volume_m3=20.0,
                max_loaders=4,
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

        await session.commit()

        carrier_id = carrier.id
        vehicle_id = vehicle.id

    await engine.dispose()

    return carrier_id, vehicle_id


async def create_redispatch_carrier() -> tuple[int, int]:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    now = datetime.now(UTC)

    async with session_maker() as session:
        repository = CarrierRepository(session)

        carrier = await repository.create_carrier(
            CarrierCompany(
                company_name="CargoPT Redispatch Carrier",
                contact_name="Segundo Transportador E2E",
                phone="+351920000002",
                telegram_user_id=880002,
                telegram_username="cargopt_e2e_redispatch",
                status=CarrierStatus.ACTIVE,
                paid_until=now + timedelta(days=30),
                assembly_required=False,
                packing_required=False,
                operating_regions="Lisboa",
                profile_completed_at=now,
                current_profile_step=None,
                internal_note="positive redispatch fixture",
                created_at=now,
                updated_at=now,
            )
        )

        vehicle = await repository.create_vehicle(
            CarrierVehicle(
                carrier_id=carrier.id,
                vehicle_type="large_van",
                payload_kg=2200,
                volume_m3=22.0,
                max_loaders=4,
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

        await session.commit()

        carrier_id = carrier.id
        vehicle_id = vehicle.id

    await engine.dispose()

    return carrier_id, vehicle_id


async def wait_for_server(base_url: str) -> None:
    import httpx

    async with httpx.AsyncClient() as client:
        for _ in range(100):
            try:
                response = await client.get(
                    f"{base_url}/health",
                    timeout=0.5,
                )
                if response.status_code == 200:
                    return
            except Exception:
                pass

            await asyncio.sleep(0.1)

    raise RuntimeError("local FastAPI server did not become ready")


async def accept_generated_offer(job_id: int) -> dict:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        repository = JobRepository(session)

        result = await session.execute(
            select(JobOffer)
            .where(JobOffer.job_id == job_id)
            .order_by(JobOffer.id)
        )
        offers = list(result.scalars().all())

        if len(offers) != 1:
            raise AssertionError(
                f"expected exactly one generated offer, got {len(offers)}"
            )

        offer = offers[0]

        if offer.status != JobOfferStatus.PENDING:
            raise AssertionError(
                f"expected pending offer, got {offer.status}"
            )

        service = JobOfferService(repository)
        accepted = await service.accept_offer_without_assignment(offer.id)

        accepted.price_cents = 12500
        accepted.carrier_note = "Preço final, incluindo dois ajudantes."
        accepted.updated_at = datetime.now(UTC)

        await session.commit()

        job = await repository.get_job_by_id(job_id)

        result_data = {
            "offer_id": accepted.id,
            "offer_status": str(accepted.status),
            "job_status": str(job.status),
            "price_cents": accepted.price_cents,
            "carrier_note": accepted.carrier_note,
        }

    await engine.dispose()

    return result_data


async def accept_specific_offer(
    *,
    offer_id: int,
    expected_carrier_id: int,
) -> dict:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        repository = JobRepository(session)
        offer = await repository.get_offer_by_id(offer_id)

        if offer is None:
            raise AssertionError(
                f"offer {offer_id} was not found"
            )

        if offer.carrier_id != expected_carrier_id:
            raise AssertionError(
                "offer carrier mismatch: "
                f"{offer.carrier_id} != {expected_carrier_id}"
            )

        if offer.status != JobOfferStatus.PENDING:
            raise AssertionError(
                f"expected pending offer, got {offer.status}"
            )

        service = JobOfferService(repository)
        accepted = await service.accept_offer_without_assignment(
            offer.id
        )

        accepted.price_cents = 13750
        accepted.carrier_note = (
            "Segunda proposta após nova procura."
        )
        accepted.updated_at = datetime.now(UTC)

        await session.commit()

        job = await repository.get_job_by_id(
            accepted.job_id
        )

        result_data = {
            "offer_id": accepted.id,
            "carrier_id": accepted.carrier_id,
            "offer_status": str(accepted.status),
            "job_status": str(job.status),
            "price_cents": accepted.price_cents,
            "carrier_note": accepted.carrier_note,
        }

    await engine.dispose()
    return result_data


async def inspect_database(job_id: int, offer_id: int) -> dict:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        job_repository = JobRepository(session)

        job = await job_repository.get_job_by_id(job_id)
        offer = await job_repository.get_offer_by_id(offer_id)

        offers_result = await session.execute(
            select(JobOffer)
            .where(JobOffer.job_id == job_id)
            .order_by(JobOffer.id)
        )
        offers = list(offers_result.scalars().all())

        accepted_offer = (
            await job_repository.get_accepted_offer_by_job_id(
                job_id
            )
        )

        addresses = await job_repository.list_addresses_by_job(job_id)
        items = await job_repository.list_items_by_job(job_id)

        result = {
            "job": {
                "id": job.id,
                "status": str(job.status),
                "source": job.source,
                "source_locale": job.source_locale,
                "customer_name": job.customer_name,
                "client_phone": job.client_phone,
                "preferred_contact": job.preferred_contact,
                "tracking_token": job.tracking_token,
                "required_loaders": job.required_loaders,
                "estimated_volume_m3": job.estimated_volume_m3,
                "comment": job.comment,
                "client_confirmation_status":
                    job.client_confirmation_status,
                "carrier_confirmation_status":
                    job.carrier_confirmation_status,
            },
            "offer": {
                "id": offer.id,
                "status": str(offer.status),
                "price_cents": offer.price_cents,
                "carrier_note": offer.carrier_note,
            },
            "offers": [
                {
                    "id": current_offer.id,
                    "carrier_id": current_offer.carrier_id,
                    "vehicle_id": current_offer.vehicle_id,
                    "status": str(current_offer.status),
                    "price_cents": current_offer.price_cents,
                    "carrier_message_chat_id":
                        current_offer.carrier_message_chat_id,
                    "carrier_message_id":
                        current_offer.carrier_message_id,
                }
                for current_offer in offers
            ],
            "accepted_offer_id": (
                accepted_offer.id
                if accepted_offer is not None
                else None
            ),
            "addresses": [
                {
                    "kind": address.kind,
                    "raw_text": address.raw_text,
                    "floor": address.floor,
                    "has_elevator": address.has_elevator,
                }
                for address in addresses
            ],
            "items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                }
                for item in items
            ],
        }

    await engine.dispose()

    return result


async def recover_submit_result(
    tracking_token: str,
    tracking_url: str,
) -> dict:
    engine = create_async_engine(DATABASE_URL)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        repository = JobRepository(session)
        job = await repository.get_job_by_tracking_token(tracking_token)

        if job is None:
            raise AssertionError(
                f"submitted job not found for token {tracking_token}"
            )

        result = await session.execute(
            select(JobOffer)
            .where(JobOffer.job_id == job.id)
            .order_by(JobOffer.id)
        )
        offers = list(result.scalars().all())

        submit_result = {
            "job_id": job.id,
            "status": str(job.status),
            "tracking_token": job.tracking_token,
            "tracking_url": tracking_url,
            "offers_count": len(offers),
            "sent_count": len(fake_bot.messages),
        }

    await engine.dispose()

    return submit_result


async def run_browser(base_url: str) -> dict:
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[dict] = []
    request_responses: list[dict] = []

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox"],
        )

        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            locale="pt-PT",
            color_scheme="light",
            reduced_motion="reduce",
            service_workers="block",
        )

        page = await context.new_page()

        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text)
                if message.type == "error"
                else None
            ),
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                {
                    "url": request.url,
                    "failure": request.failure,
                }
            ),
        )

        def record_response(response):
            if "/api/v1/" not in response.url:
                return

            request_responses.append(
                {
                    "url": response.url,
                    "method": response.request.method,
                    "status": response.status,
                }
            )

        page.on("response", record_response)

        await page.goto(base_url, wait_until="networkidle")

        await page.locator('[name="pickup"]').fill("Lisboa")
        await page.locator('[name="dropoff"]').fill("Cascais")
        await page.locator('[name="items"]').fill("Sofá e 10 caixas")
        await page.locator("[data-next]").click()

        await page.locator('[name="customer_name"]').fill(
            "CargoPT Fullstack E2E"
        )
        await page.locator('[name="requested_date"]').fill("20/07/2026")
        await page.locator('[name="client_phone"]').fill("+351910000001")
        await page.locator('[name="pickup_floor"]').fill("1")
        await page.locator(
            '[name="pickup_elevator"]'
        ).select_option("true")
        await page.locator('[name="dropoff_floor"]').fill("2")
        await page.locator(
            '[name="dropoff_elevator"]'
        ).select_option("false")
        await page.locator(
            '[name="required_loaders"]'
        ).select_option("2")
        await page.locator(
            '[name="estimated_volume_m3"]'
        ).fill("5")
        await page.locator('[name="comment"]').fill(
            "Isolated fullstack browser E2E"
        )

        async with page.expect_response(
            lambda response: (
                response.url.endswith("/api/v1/requests")
                and response.request.method == "POST"
            )
        ) as response_info:
            await page.locator('button[type="submit"]').click()

        submit_response = await response_info.value

        assert submit_response.status == 200, submit_response.status

        await page.wait_for_url(
            "**/track/*",
            timeout=15_000,
        )
        await page.wait_for_load_state("networkidle")

        tracking_url = await page.evaluate(
            "window.location.pathname"
        )
        tracking_token = tracking_url.rstrip("/").split("/")[-1]

        submit_body = await recover_submit_result(
            tracking_token,
            tracking_url,
        )

        assert submit_body["offers_count"] == 1
        assert submit_body["sent_count"] == 1
        assert submit_body["status"] == JobStatus.OFFERED
        assert submit_body["tracking_token"] == tracking_token
        assert submit_body["tracking_url"].startswith("/track/")

        waiting_visible = await page.locator(
            ".tracking-waiting-state"
        ).is_visible()

        await page.screenshot(
            path=str(OUT / "01-mobile-pending-offer.png"),
            full_page=True,
            animations="disabled",
        )

        accepted = await accept_generated_offer(submit_body["job_id"])

        assert accepted["offer_status"] == JobOfferStatus.ACCEPTED
        assert accepted["job_status"] == JobStatus.OFFERED

        await page.reload(wait_until="networkidle")

        card = page.locator(".tracking-offer-card")
        select_button = page.locator(".tracking-select-button")

        await card.wait_for(state="visible")

        company = await card.locator(
            ".tracking-offer-top strong"
        ).first.inner_text()
        price = await card.locator(
            ".tracking-offer-price"
        ).inner_text()
        note = await card.locator(
            ".tracking-offer-note"
        ).inner_text()

        assert company == "CargoPT Fullstack Carrier"
        assert price == "125 €"
        assert note == "Preço final, incluindo dois ajudantes."
        assert await select_button.is_visible()

        await page.screenshot(
            path=str(OUT / "02-mobile-accepted-offer.png"),
            full_page=True,
            animations="disabled",
        )

        async with page.expect_response(
            lambda response: (
                "/offers/" in response.url
                and response.url.endswith("/select")
                and response.request.method == "POST"
            )
        ) as selection_info:
            await select_button.click()

        selection_response = await selection_info.value
        selection_body = await selection_response.json()

        assert selection_response.status == 200, (
            selection_response.status,
            selection_body,
        )
        assert (
            selection_body["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert selection_body["selected_offer_id"] == accepted["offer_id"]

        await page.wait_for_timeout(500)

        async with page.expect_response(
            lambda response: (
                "/api/v1/track/" in response.url
                and response.request.method == "GET"
            )
        ):
            await page.reload(wait_until="networkidle")

        fail_button = page.locator(".tracking-assignment-fail")
        await fail_button.wait_for(state="visible")

        progress_label = await page.locator(
            ".progress-header-current-label"
        ).inner_text()

        horizontal_overflow = await page.evaluate(
            """
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth + 1
            """
        )

        await page.screenshot(
            path=str(OUT / "03-mobile-selected-offer.png"),
            full_page=True,
            animations="disabled",
        )

        selected_database_state = await inspect_database(
            submit_body["job_id"],
            accepted["offer_id"],
        )

        assert (
            selected_database_state["job"]["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert (
            selected_database_state["job"]
            ["client_confirmation_status"]
            is None
        )
        assert (
            selected_database_state["job"]
            ["carrier_confirmation_status"]
            is None
        )
        assert (
            selected_database_state["offer"]["status"]
            == JobOfferStatus.ACCEPTED
        )

        client_confirmation_result = await page.evaluate(
            """
            async ({token}) => {
              const response = await fetch(
                `/api/v1/track/${
                  encodeURIComponent(token)
                }/assignment/confirm`,
                {
                  method: "POST",
                  headers: {
                    "Accept": "application/json"
                  }
                }
              );

              let body = null;

              try {
                body = await response.json();
              } catch (error) {
                body = {
                  parse_error: String(error)
                };
              }

              return {
                status: response.status,
                body
              };
            }
            """,
            {
                "token": tracking_token,
            },
        )

        client_confirmation_body = (
            client_confirmation_result["body"]
        )

        assert client_confirmation_result["status"] == 200, (
            client_confirmation_result
        )
        assert (
            client_confirmation_body["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert (
            client_confirmation_body[
                "client_confirmation_status"
            ]
            == "confirmed"
        )
        assert (
            client_confirmation_body[
                "carrier_confirmation_status"
            ]
            is None
        )

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        client_confirmation_recorded_visible = (
            await page.locator(
                ".tracking-assignment-actions"
            ).is_visible()
        )

        assert client_confirmation_recorded_visible is True

        client_confirmation_progress_label = (
            await page.locator(
                ".progress-header-current-label"
            ).inner_text()
        )

        await page.screenshot(
            path=str(
                OUT
                / "04-mobile-client-confirmed.png"
            ),
            full_page=True,
            animations="disabled",
        )

        carrier_confirmation = (
            await confirm_carrier_assignment(
                submit_body["job_id"]
            )
        )

        assert carrier_confirmation["answers"]
        assert carrier_confirmation["message_edits"]

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        final_progress_label = await page.locator(
            ".progress-header-current-label"
        ).inner_text()

        final_horizontal_overflow = await page.evaluate(
            """
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth + 1
            """
        )

        await page.screenshot(
            path=str(
                OUT
                / "05-mobile-both-confirmed.png"
            ),
            full_page=True,
            animations="disabled",
        )

        database_state = await inspect_database(
            submit_body["job_id"],
            accepted["offer_id"],
        )

        assert (
            database_state["job"]["status"]
            == JobStatus.ASSIGNED
        )
        assert (
            database_state["job"]
            ["client_confirmation_status"]
            == "confirmed"
        )
        assert (
            database_state["job"]
            ["carrier_confirmation_status"]
            == "confirmed"
        )
        assert (
            database_state["offer"]["status"]
            == JobOfferStatus.ACCEPTED
        )

        (
            redispatch_carrier_id,
            redispatch_vehicle_id,
        ) = await create_redispatch_carrier()

        bot_message_count_before_reopen = len(
            fake_bot.messages
        )

        reopen_result = await page.evaluate(
            """
            async ({token}) => {
              const response = await fetch(
                `/api/v1/track/${
                  encodeURIComponent(token)
                }/assignment/fail`,
                {
                  method: "POST",
                  headers: {
                    "Accept": "application/json"
                  }
                }
              );

              let body = null;

              try {
                body = await response.json();
              } catch (error) {
                body = {
                  parse_error: String(error)
                };
              }

              return {
                status: response.status,
                body
              };
            }
            """,
            {
                "token": tracking_token,
            },
        )

        reopen_body = reopen_result["body"]

        assert reopen_result["status"] == 200, reopen_result
        assert reopen_body["status"] == JobStatus.OFFERED
        assert (
            reopen_body["client_confirmation_status"]
            is None
        )
        assert (
            reopen_body["carrier_confirmation_status"]
            is None
        )

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        reopen_progress_label = await page.locator(
            ".progress-header-current-label"
        ).inner_text()

        reopen_waiting_state_count = await page.locator(
            ".tracking-waiting-state"
        ).count()

        reopen_offer_card_count = await page.locator(
            ".tracking-offer-card"
        ).count()

        reopen_select_button_count = await page.locator(
            ".tracking-select-button"
        ).count()

        reopen_fail_button_count = await page.locator(
            ".tracking-assignment-fail"
        ).count()

        reopen_horizontal_overflow = await page.evaluate(
            """
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth + 1
            """
        )

        await page.screenshot(
            path=str(
                OUT
                / "06-mobile-positive-redispatch.png"
            ),
            full_page=True,
            animations="disabled",
        )

        reopen_database_state = await inspect_database(
            submit_body["job_id"],
            accepted["offer_id"],
        )

        assert (
            reopen_database_state["job"]["status"]
            == JobStatus.OFFERED
        )
        assert (
            reopen_database_state["job"]
            ["client_confirmation_status"]
            is None
        )
        assert (
            reopen_database_state["job"]
            ["carrier_confirmation_status"]
            is None
        )
        assert (
            reopen_database_state["accepted_offer_id"]
            is None
        )

        offers_by_id = {
            offer_state["id"]: offer_state
            for offer_state in (
                reopen_database_state["offers"]
            )
        }

        assert len(offers_by_id) == 2

        original_offer_state = offers_by_id[
            accepted["offer_id"]
        ]

        assert (
            original_offer_state["status"]
            == JobOfferStatus.CANCELLED
        )
        assert (
            original_offer_state["carrier_id"]
            != redispatch_carrier_id
        )

        redispatch_offers = [
            offer_state
            for offer_state in offers_by_id.values()
            if offer_state["id"] != accepted["offer_id"]
        ]

        assert len(redispatch_offers) == 1

        redispatch_offer = redispatch_offers[0]

        assert (
            redispatch_offer["carrier_id"]
            == redispatch_carrier_id
        )
        assert (
            redispatch_offer["vehicle_id"]
            == redispatch_vehicle_id
        )
        assert (
            redispatch_offer["status"]
            == JobOfferStatus.PENDING
        )
        assert (
            redispatch_offer["carrier_message_chat_id"]
            == 880002
        )
        assert (
            redispatch_offer["carrier_message_id"]
            is not None
        )

        redispatch_bot_messages = fake_bot.messages[
            bot_message_count_before_reopen:
        ]

        assert len(redispatch_bot_messages) == 1

        redispatch_bot_message = (
            redispatch_bot_messages[0]
        )

        assert (
            redispatch_bot_message["method"]
            == "send_message"
        )
        assert (
            redispatch_bot_message["chat_id"]
            == 880002
        )
        assert (
            "<b>Новая заявка #"
            in redispatch_bot_message["text"]
        )

        redispatch_keyboard = (
            redispatch_bot_message["kwargs"]
            ["reply_markup"]
            ["inline_keyboard"]
        )

        assert (
            redispatch_keyboard[0][0]["callback_data"]
            == (
                "offer:accept:"
                f"{redispatch_offer['id']}"
            )
        )

        assert reopen_progress_label == "À procura"
        assert reopen_waiting_state_count == 1
        assert reopen_offer_card_count == 0
        assert reopen_select_button_count == 0
        assert reopen_fail_button_count == 0
        assert reopen_horizontal_overflow is False

        stale_offer_selection = await page.evaluate(
            """
            async ({token, offerId}) => {
              const response = await fetch(
                `/api/v1/track/${
                  encodeURIComponent(token)
                }/offers/${offerId}/select`,
                {
                  method: "POST",
                  headers: {
                    "Accept": "application/json"
                  }
                }
              );

              let body = null;

              try {
                body = await response.json();
              } catch (error) {
                body = {
                  parse_error: String(error)
                };
              }

              return {
                status: response.status,
                body
              };
            }
            """,
            {
                "token": tracking_token,
                "offerId": accepted["offer_id"],
            },
        )

        assert stale_offer_selection["status"] == 409
        assert (
            stale_offer_selection["body"]["detail"]
            == "offer is not accepted by carrier"
        )

        redispatch_acceptance = await accept_specific_offer(
            offer_id=redispatch_offer["id"],
            expected_carrier_id=redispatch_carrier_id,
        )

        assert (
            redispatch_acceptance["offer_status"]
            == JobOfferStatus.ACCEPTED
        )
        assert (
            redispatch_acceptance["job_status"]
            == JobStatus.OFFERED
        )
        assert (
            redispatch_acceptance["carrier_id"]
            == redispatch_carrier_id
        )

        await page.reload(wait_until="networkidle")

        redispatch_card = page.locator(
            ".tracking-offer-card"
        )
        redispatch_select_button = page.locator(
            ".tracking-select-button"
        )

        await redispatch_card.wait_for(state="visible")

        redispatch_ui_company = await redispatch_card.locator(
            ".tracking-offer-top strong"
        ).first.inner_text()
        redispatch_ui_price = await redispatch_card.locator(
            ".tracking-offer-price"
        ).inner_text()
        redispatch_ui_note = await redispatch_card.locator(
            ".tracking-offer-note"
        ).inner_text()

        assert await redispatch_card.count() == 1
        assert await redispatch_select_button.count() == 1
        assert await redispatch_select_button.is_visible()
        assert (
            redispatch_ui_company
            == "CargoPT Redispatch Carrier"
        )
        assert (
            redispatch_ui_price.replace("\u00a0", " ")
            == "137,5 €"
        )
        assert (
            redispatch_ui_note
            == "Segunda proposta após nova procura."
        )

        await page.screenshot(
            path=str(
                OUT
                / "07-mobile-redispatch-accepted.png"
            ),
            full_page=True,
            animations="disabled",
        )

        bot_message_count_before_second_selection = len(
            fake_bot.messages
        )

        async with page.expect_response(
            lambda response: (
                response.url.endswith(
                    f"/offers/{redispatch_offer['id']}/select"
                )
                and response.request.method == "POST"
            )
        ) as redispatch_selection_info:
            await redispatch_select_button.click()

        redispatch_selection_response = (
            await redispatch_selection_info.value
        )
        redispatch_selection_body = (
            await redispatch_selection_response.json()
        )

        assert redispatch_selection_response.status == 200, (
            redispatch_selection_response.status,
            redispatch_selection_body,
        )
        assert (
            redispatch_selection_body["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert (
            redispatch_selection_body["selected_offer_id"]
            == redispatch_offer["id"]
        )

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        second_selected_fail_button = page.locator(
            ".tracking-assignment-fail"
        )
        await second_selected_fail_button.wait_for(
            state="visible"
        )

        second_selected_progress_label = (
            await page.locator(
                ".progress-header-current-label"
            ).inner_text()
        )
        second_selected_offer_card_count = await page.locator(
            ".tracking-offer-card"
        ).count()
        second_selected_company = await page.locator(
            ".tracking-offer-card "
            ".tracking-offer-top strong"
        ).first.inner_text()
        second_selected_horizontal_overflow = (
            await page.evaluate(
                """
                document.documentElement.scrollWidth >
                document.documentElement.clientWidth + 1
                """
            )
        )

        await page.screenshot(
            path=str(
                OUT
                / "08-mobile-redispatch-selected.png"
            ),
            full_page=True,
            animations="disabled",
        )

        post_redispatch_database_state = (
            await inspect_database(
                submit_body["job_id"],
                accepted["offer_id"],
            )
        )

        assert (
            post_redispatch_database_state["job"]["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert (
            post_redispatch_database_state["job"]
            ["client_confirmation_status"]
            is None
        )
        assert (
            post_redispatch_database_state["job"]
            ["carrier_confirmation_status"]
            is None
        )
        assert (
            post_redispatch_database_state[
                "accepted_offer_id"
            ]
            == redispatch_offer["id"]
        )

        post_offers_by_id = {
            offer_state["id"]: offer_state
            for offer_state in (
                post_redispatch_database_state["offers"]
            )
        }
        post_original_offer = post_offers_by_id[
            accepted["offer_id"]
        ]
        post_redispatch_offer = post_offers_by_id[
            redispatch_offer["id"]
        ]

        assert (
            post_original_offer["status"]
            == JobOfferStatus.CANCELLED
        )
        assert (
            post_redispatch_offer["status"]
            == JobOfferStatus.ACCEPTED
        )
        assert (
            post_redispatch_offer["carrier_id"]
            == redispatch_carrier_id
        )
        assert post_redispatch_offer["price_cents"] == 13750

        redispatch_assignment_messages = (
            fake_bot.messages[
                bot_message_count_before_second_selection:
            ]
        )

        assert any(
            message.get("method") == "send_message"
            and message.get("chat_id") == 880002
            and (
                "Клиент выбрал ваше предложение"
                in message.get("text", "")
            )
            for message in redispatch_assignment_messages
        )

        assert second_selected_progress_label == "Escolha"
        assert second_selected_offer_card_count == 1
        assert (
            second_selected_company
            == "CargoPT Redispatch Carrier"
        )
        assert second_selected_horizontal_overflow is False

        second_client_confirmation_result = await page.evaluate(
            """
            async ({token}) => {
              const response = await fetch(
                `/api/v1/track/${
                  encodeURIComponent(token)
                }/assignment/confirm`,
                {
                  method: "POST",
                  headers: {
                    "Accept": "application/json"
                  }
                }
              );

              let body = null;

              try {
                body = await response.json();
              } catch (error) {
                body = {
                  parse_error: String(error)
                };
              }

              return {
                status: response.status,
                body
              };
            }
            """,
            {
                "token": tracking_token,
            },
        )

        second_client_confirmation_body = (
            second_client_confirmation_result["body"]
        )

        assert (
            second_client_confirmation_result["status"]
            == 200
        ), second_client_confirmation_result
        assert (
            second_client_confirmation_body["status"]
            == JobStatus.ASSIGNED_PENDING_CONFIRMATION
        )
        assert (
            second_client_confirmation_body[
                "client_confirmation_status"
            ]
            == "confirmed"
        )
        assert (
            second_client_confirmation_body[
                "carrier_confirmation_status"
            ]
            is None
        )

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        second_client_confirmation_actions_visible = (
            await page.locator(
                ".tracking-assignment-actions"
            ).is_visible()
        )
        second_client_confirmation_progress_label = (
            await page.locator(
                ".progress-header-current-label"
            ).inner_text()
        )

        assert (
            second_client_confirmation_actions_visible
            is True
        )
        assert (
            second_client_confirmation_progress_label
            == "Escolha"
        )

        await page.screenshot(
            path=str(
                OUT
                / "09-mobile-redispatch-client-confirmed.png"
            ),
            full_page=True,
            animations="disabled",
        )

        bot_message_count_before_second_carrier_confirmation = len(
            fake_bot.messages
        )

        second_carrier_confirmation = (
            await confirm_carrier_assignment(
                submit_body["job_id"]
            )
        )

        assert (
            second_carrier_confirmation["telegram_user_id"]
            == 880002
        )
        assert second_carrier_confirmation["answers"]
        assert second_carrier_confirmation["message_edits"]
        assert (
            second_carrier_confirmation["new_bot_messages"]
            == 1
        )

        second_final_messages = fake_bot.messages[
            bot_message_count_before_second_carrier_confirmation:
        ]

        assert len(second_final_messages) == 1
        assert (
            second_final_messages[0]["method"]
            == "send_message"
        )
        assert (
            second_final_messages[0]["chat_id"]
            == 880002
        )
        assert (
            "подтверждена обеими сторонами"
            in second_final_messages[0]["text"]
        )

        await page.wait_for_timeout(300)
        await page.reload(wait_until="networkidle")

        redispatch_final_progress_label = (
            await page.locator(
                ".progress-header-current-label"
            ).inner_text()
        )
        redispatch_final_horizontal_overflow = (
            await page.evaluate(
                """
                document.documentElement.scrollWidth >
                document.documentElement.clientWidth + 1
                """
            )
        )

        await page.screenshot(
            path=str(
                OUT
                / "10-mobile-redispatch-both-confirmed.png"
            ),
            full_page=True,
            animations="disabled",
        )

        redispatch_final_database_state = (
            await inspect_database(
                submit_body["job_id"],
                accepted["offer_id"],
            )
        )

        assert (
            redispatch_final_database_state["job"]["status"]
            == JobStatus.ASSIGNED
        )
        assert (
            redispatch_final_database_state["job"]
            ["client_confirmation_status"]
            == "confirmed"
        )
        assert (
            redispatch_final_database_state["job"]
            ["carrier_confirmation_status"]
            == "confirmed"
        )
        assert (
            redispatch_final_database_state[
                "accepted_offer_id"
            ]
            == redispatch_offer["id"]
        )

        redispatch_final_offers_by_id = {
            offer_state["id"]: offer_state
            for offer_state in (
                redispatch_final_database_state["offers"]
            )
        }

        redispatch_final_original_offer = (
            redispatch_final_offers_by_id[
                accepted["offer_id"]
            ]
        )
        redispatch_final_selected_offer = (
            redispatch_final_offers_by_id[
                redispatch_offer["id"]
            ]
        )

        assert (
            redispatch_final_original_offer["status"]
            == JobOfferStatus.CANCELLED
        )
        assert (
            redispatch_final_selected_offer["status"]
            == JobOfferStatus.ACCEPTED
        )
        assert (
            redispatch_final_selected_offer["carrier_id"]
            == redispatch_carrier_id
        )
        assert (
            redispatch_final_selected_offer["price_cents"]
            == 13750
        )

        assert redispatch_final_progress_label == "Confirmado"
        assert redispatch_final_horizontal_overflow is False

        assert horizontal_overflow is False
        assert final_horizontal_overflow is False
        assert page_errors == []
        assert failed_requests == []

        await context.close()
        await browser.close()

    return {
        "submitResponse": submit_body,
        "waitingVisibleBeforeAcceptance": waiting_visible,
        "acceptedOffer": accepted,
        "offerUi": {
            "company": company,
            "price": price,
            "note": note,
            "selectButtonVisible": True,
        },
        "selectionResponse": selection_body,
        "selectedUi": {
            "failButtonVisible": True,
            "progressLabel": progress_label,
            "horizontalOverflow": horizontal_overflow,
        },
        "selectedDatabaseState":
            selected_database_state,
        "clientConfirmationResponse":
            client_confirmation_body,
        "clientConfirmationUi": {
            "recordedVisible":
                client_confirmation_recorded_visible,
            "progressLabel":
                client_confirmation_progress_label,
        },
        "carrierConfirmation":
            carrier_confirmation,
        "finalUi": {
            "progressLabel": final_progress_label,
            "horizontalOverflow":
                final_horizontal_overflow,
        },
        "databaseState": database_state,
        "redispatchCarrier": {
            "carrierId": redispatch_carrier_id,
            "vehicleId": redispatch_vehicle_id,
        },
        "reopenResponse": reopen_body,
        "reopenHttpStatus": reopen_result["status"],
        "reopenDatabaseState": reopen_database_state,
        "reopenUi": {
            "progressLabel": reopen_progress_label,
            "waitingStateCount":
                reopen_waiting_state_count,
            "offerCardCount":
                reopen_offer_card_count,
            "selectButtonCount":
                reopen_select_button_count,
            "failButtonCount":
                reopen_fail_button_count,
            "horizontalOverflow":
                reopen_horizontal_overflow,
        },
        "redispatchOffer": redispatch_offer,
        "redispatchBotMessages":
            redispatch_bot_messages,
        "staleOfferSelection":
            stale_offer_selection,
        "redispatchAcceptance":
            redispatch_acceptance,
        "redispatchOfferUi": {
            "company": redispatch_ui_company,
            "price": redispatch_ui_price,
            "note": redispatch_ui_note,
            "selectButtonVisible": True,
        },
        "redispatchSelectionResponse":
            redispatch_selection_body,
        "redispatchSelectedUi": {
            "progressLabel":
                second_selected_progress_label,
            "offerCardCount":
                second_selected_offer_card_count,
            "company":
                second_selected_company,
            "failButtonVisible": True,
            "horizontalOverflow":
                second_selected_horizontal_overflow,
        },
        "postRedispatchDatabaseState":
            post_redispatch_database_state,
        "redispatchAssignmentMessages":
            redispatch_assignment_messages,
        "secondClientConfirmationResponse":
            second_client_confirmation_body,
        "secondClientConfirmationUi": {
            "actionsVisible":
                second_client_confirmation_actions_visible,
            "progressLabel":
                second_client_confirmation_progress_label,
        },
        "secondCarrierConfirmation":
            second_carrier_confirmation,
        "secondFinalMessages":
            second_final_messages,
        "redispatchFinalUi": {
            "progressLabel":
                redispatch_final_progress_label,
            "horizontalOverflow":
                redispatch_final_horizontal_overflow,
        },
        "redispatchFinalDatabaseState":
            redispatch_final_database_state,
        "fakeBotMessages": fake_bot.messages,
        "requestResponses": request_responses,
        "consoleErrors": console_errors,
        "pageErrors": page_errors,
        "failedRequests": failed_requests,
    }


async def main() -> None:
    carrier_id = None
    vehicle_id = None
    server = None
    server_task = None

    try:
        carrier_id, vehicle_id = await create_schema_and_carrier()

        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=PORT,
            log_level="warning",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server_task = asyncio.create_task(server.serve())

        base_url = f"http://127.0.0.1:{PORT}"
        await wait_for_server(base_url)

        browser_result = await run_browser(base_url)

        result = {
            "environment": os.environ["ENVIRONMENT"],
            "databaseUrl": DATABASE_URL,
            "productionDatabaseUsed": False,
            "realTelegramUsed": False,
            "port": PORT,
            "carrierId": carrier_id,
            "vehicleId": vehicle_id,
            "browser": browser_result,
        }

        (OUT / "results.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print("FULLSTACK_SCENARIO_OK")
        print("PRODUCTION_DATABASE_USED=false")
        print("REAL_TELEGRAM_USED=false")
        print(f"JOB_ID={browser_result['submitResponse']['job_id']}")
        print(
            "INITIAL_STATUS="
            f"{browser_result['submitResponse']['status']}"
        )
        print(
            "FINAL_STATUS="
            f"{browser_result['redispatchFinalDatabaseState']['job']['status']}"
        )
        print(
            "STALE_OFFER_SELECT_STATUS="
            f"{browser_result['staleOfferSelection']['status']}"
        )
        print(
            "REDISPATCH_CARRIER_ID="
            f"{browser_result['redispatchCarrier']['carrierId']}"
        )
        print(
            "REDISPATCH_OFFER_ID="
            f"{browser_result['redispatchOffer']['id']}"
        )
        print(
            "FAKE_BOT_MESSAGES="
            f"{len(browser_result['fakeBotMessages'])}"
        )
        print(f"OUTPUT={OUT}")

    finally:
        if server is not None:
            server.should_exit = True

        if server_task is not None:
            try:
                await asyncio.wait_for(server_task, timeout=10)
            except Exception:
                server_task.cancel()

        app.dependency_overrides.clear()


asyncio.run(main())
