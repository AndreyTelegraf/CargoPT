"""Isolated date guard regressions. No network or production database."""
import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
from app.services.offer_distribution import OfferDistributionService
from app.services.job_matching import MatchingReason


async def exercise():
    now = datetime(2026, 11, 5, 22, tzinfo=UTC)
    cases = [
        ("yesterday", now - timedelta(days=1), True),
        ("last year", now - timedelta(days=365), True),
        ("exactly now", now, False),
        ("minutes", now + timedelta(minutes=3), False),
        ("24h", now + timedelta(hours=24), False),
        ("7d", now + timedelta(days=7), False),
        ("naive past UTC", (now - timedelta(seconds=1)).replace(tzinfo=None), True),
        ("naive future UTC", (now + timedelta(minutes=3)).replace(tzinfo=None), False),
        ("aware past", (now - timedelta(seconds=1)).astimezone(timezone(timedelta(hours=3))), True),
        ("none", None, False),
    ]
    for name, date, past in cases:
        for accepted in (False, True):
            repo = SimpleNamespace(
                update_job_status=AsyncMock(),
                list_offer_carrier_ids_by_job=AsyncMock(return_value=set()),
                list_addresses_by_job=AsyncMock(return_value=[]),
                list_offers_by_job=AsyncMock(return_value=[SimpleNamespace(status="accepted")] if accepted else []),
            )
            matching = SimpleNamespace(find_matching_result_for_job=AsyncMock(return_value=SimpleNamespace(
                vehicles=[SimpleNamespace(id=1, carrier_id=1)],
                reason=MatchingReason.MATCH_FOUND, regions=["Lisboa"],
            )))
            offers = SimpleNamespace(create_offer=AsyncMock(return_value=SimpleNamespace(id=1)))
            service = OfferDistributionService(matching_service=matching, offer_service=offers, job_repository=repo)
            job = SimpleNamespace(id=1, requested_date=date, updated_at=now, status="offered")
            with patch("app.domain.requested_date.datetime") as clock:
                clock.now.return_value = now
                result = await service.create_offer_distribution_for_job(job)
                if past:
                    assert not result.offers, f"{name}: created offers for past date"
                    offers.create_offer.assert_not_awaited()
                    matching.find_matching_result_for_job.assert_not_awaited()
                    assert str(result.matching_reason) == "requested_date_passed"
                    expected = "offered" if accepted else "manual_review_required"
                    assert all(str(c.kwargs["status"]) == expected for c in repo.update_job_status.await_args_list)
                    await service.create_offer_distribution_for_job(job)
                    offers.create_offer.assert_not_awaited()
                else:
                    assert len(result.offers) == 1, name
    print("DISTRIBUTION_DATE_REGRESSION_OK cases=20 plus repeat calls")


if __name__ == "__main__":
    asyncio.run(exercise())
