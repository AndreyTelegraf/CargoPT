import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.config import settings
from app.services.request_intake import RequestIntakeAddress
from app.services.request_intake import RequestIntakeInput
from app.services.request_intake import RequestIntakeItem
from app.services.request_intake import RequestIntakeService
from app.services.request_intake import WebRequestRateLimitError


class FakeJobRepository:
    async def list_recent_web_jobs_for_contact(self, **kwargs):
        return []

    async def count_recent_web_jobs_for_contact(self, **kwargs):
        assert kwargs["customer_email"] == "limited@example.test"
        return settings.web_request_contact_daily_limit


class ForbiddenDependency:
    def __getattr__(self, name):
        raise AssertionError(f"rate-limited request used dependency: {name}")


async def main():
    service = RequestIntakeService(
        job_repository=FakeJobRepository(),
        carrier_repository=ForbiddenDependency(),
        bot=ForbiddenDependency(),
    )
    request = RequestIntakeInput(
        source_locale="en",
        customer_name="Limited Client",
        customer_email="limited@example.test",
        preferred_contact="email",
        client_phone=None,
        client_whatsapp=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
        utm_content=None,
        landing_version=None,
        requested_date=datetime.now(UTC) + timedelta(days=1),
        addresses=(
            RequestIntakeAddress("pickup", "Lisboa", None, None),
            RequestIntakeAddress("dropoff", "Porto", None, None),
        ),
        items=(RequestIntakeItem("Boxes", 2),),
    )
    try:
        await service.submit_web_intake(request)
    except WebRequestRateLimitError:
        pass
    else:
        raise AssertionError("daily contact limit was not enforced")
    print("WEB_REQUEST_CONTACT_RATE_LIMIT_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
