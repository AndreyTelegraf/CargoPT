import asyncio
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService


class FakeJobRepository:
    def __init__(self, job, offers):
        self.job = job
        self.offers = offers

    async def list_recent_web_jobs_for_contact(self, **kwargs):
        assert kwargs["customer_email"] == "ford2008@inbox.ru"
        assert kwargs["client_phone"] == "+351965737522"
        return [self.job]

    async def list_offers_by_job(self, job_id):
        assert job_id == 103
        return self.offers


class ForbiddenDependency:
    def __getattr__(self, name):
        raise AssertionError(f"duplicate path must not use dependency: {name}")


async def main() -> None:
    existing_job = SimpleNamespace(
        id=103,
        source_locale="ru",
        requested_date=None,
        needs_assembly=False,
        needs_packing=False,
        needs_tail_lift=False,
        needs_crane=False,
        needs_mobile_lift=False,
        required_loaders=0,
        estimated_payload_kg=None,
        estimated_volume_m3=0.0001,
        comment=None,
        addresses=[
            SimpleNamespace(
                kind="pickup",
                raw_text="Ovar",
                floor=1,
                has_elevator=False,
            ),
            SimpleNamespace(
                kind="dropoff",
                raw_text="Lisboa",
                floor=1,
                has_elevator=False,
            ),
        ],
        items=[
            SimpleNamespace(
                description="Роутер 150 грам коробка 10х15х5 см",
                quantity=None,
            )
        ],
        tracking_token="existing-token",
        status="offered",
        created_at=datetime.now(UTC),
    )

    offers = [
        SimpleNamespace(carrier_message_id=1001),
        SimpleNamespace(carrier_message_id=1002),
        SimpleNamespace(carrier_message_id=None),
    ]

    service = RequestIntakeService(
        job_repository=FakeJobRepository(existing_job, offers),
        carrier_repository=ForbiddenDependency(),
        bot=ForbiddenDependency(),
    )

    result = await service.submit_web_intake(
        RequestIntakeInput(
            source_locale="ru",
            customer_name="Vold",
            customer_email="ford2008@inbox.ru",
            preferred_contact="phone",
            client_phone="+351965737522",
            client_whatsapp=None,
            utm_source=None,
            utm_medium=None,
            utm_campaign=None,
            utm_content=None,
            landing_version=None,
            requested_date=None,
            addresses=(
                RequestIntakeAddress("pickup", " OVAR ", 1, False),
                RequestIntakeAddress("dropoff", "Lisboa", 1, False),
            ),
            items=(
                RequestIntakeItem(
                    "Роутер 150 грам коробка 10х15х5 см",
                    None,
                ),
            ),
            required_loaders=0,
            estimated_volume_m3=0.0001,
        )
    )

    assert result.job is existing_job
    assert result.job.tracking_token == "existing-token"
    assert result.offers_count == 3
    assert result.sent_count == 2

    print("WEB_REQUEST_DUPLICATE_GUARD_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
