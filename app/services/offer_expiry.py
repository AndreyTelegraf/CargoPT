from datetime import UTC
from datetime import datetime

from app.domain.job_status import JobStatus
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.carrier_search import CarrierSearchService
from app.services.job_matching import JobMatchingService
from app.services.job_escalation import escalate_job_to_manual_review
from app.services.job_escalation import hold_short_lead_job_for_manual_review
from app.services.job_offer import JobOfferService
from app.services.offer_distribution import OfferDistributionService
from app.services.offer_notification import send_job_offers_to_carriers


async def process_expired_pending_offers(
    *,
    bot,
    session,
    limit: int = 100,
) -> int:
    now = datetime.now(UTC)

    job_repository = JobRepository(session)
    carrier_repository = CarrierRepository(session)

    expired_offers = await job_repository.list_expired_pending_offers(
        now=now,
        limit=limit,
    )

    if not expired_offers:
        return 0

    affected_job_ids: set[int] = set()

    for offer in expired_offers:
        expired = await job_repository.expire_offer_if_pending(
            offer_id=offer.id,
            expired_at=now,
        )
        if expired is not None:
            affected_job_ids.add(expired.job_id)

    distribution = OfferDistributionService(
        matching_service=JobMatchingService(
            CarrierSearchService(carrier_repository)
        ),
        offer_service=JobOfferService(job_repository),
        job_repository=job_repository,
    )

    for job_id in sorted(affected_job_ids):
        job = await job_repository.get_job_by_id(job_id)

        if job is None:
            continue

        if job.status != JobStatus.OFFERED:
            continue

        offers = await job_repository.list_offers_by_job(job.id)
        has_accepted_offer = any(
            offer.status == "accepted"
            for offer in offers
        )

        if has_accepted_offer:
            continue

        if await hold_short_lead_job_for_manual_review(
            bot=bot,
            job=job,
            job_repository=job_repository,
            now=now,
        ):
            continue

        distribution_result = await distribution.create_offer_distribution_for_job(
            job,
            limit=5,
            expires_in_minutes=60,
        )
        new_offers = distribution_result.offers

        if new_offers:
            await send_job_offers_to_carriers(
                bot=bot,
                job=job,
                offers=new_offers,
                job_repository=job_repository,
                carrier_repository=carrier_repository,
            )
        else:
            await escalate_job_to_manual_review(
                bot=bot,
                job=job,
                job_repository=job_repository,
                matching_reason=distribution_result.matching_reason,
                matching_regions=distribution_result.matching_regions,
            )

    return len(expired_offers)
