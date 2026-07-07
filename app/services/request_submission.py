from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from app.models.job import Job
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository
from app.services.carrier_search import CarrierSearchService
from app.services.job_escalation import escalate_job_to_manual_review
from app.services.job_matching import JobMatchingService
from app.services.job_offer import JobOfferService
from app.services.offer_distribution import OfferDistributionService
from app.services.offer_notification import send_job_offers_to_carriers


class ClientJobLimitError(ValueError):
    pass


@dataclass(frozen=True)
class RequestSubmissionResult:
    job: Job
    offers_count: int
    sent_count: int


class RequestSubmissionService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        carrier_repository: CarrierRepository,
        bot,
    ) -> None:
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository
        self.bot = bot

    async def submit_existing_job(
        self,
        *,
        job_id: int,
        comment: str | None,
        client_telegram_user_id: int | None = None,
        enforce_telegram_client_limits: bool = False,
    ) -> RequestSubmissionResult:
        if enforce_telegram_client_limits:
            if client_telegram_user_id is None:
                raise ValueError("client_telegram_user_id is required for telegram client limits")

            active_jobs = await self.job_repository.count_active_client_jobs(
                client_telegram_user_id
            )
            if active_jobs >= 2:
                raise ClientJobLimitError("active_job_limit_reached")

            sent_since = datetime.now(UTC) - timedelta(hours=24)
            sent_jobs = await self.job_repository.count_sent_client_jobs_since(
                client_telegram_user_id,
                sent_since,
            )
            if sent_jobs >= 3:
                raise ClientJobLimitError("daily_sent_job_limit_reached")

        job = await self.job_repository.update_comment_and_status(
            job_id=job_id,
            comment=comment,
            status="ready_for_matching",
            updated_at=datetime.now(UTC),
        )

        distribution = OfferDistributionService(
            matching_service=JobMatchingService(
                CarrierSearchService(self.carrier_repository)
            ),
            offer_service=JobOfferService(self.job_repository),
            job_repository=self.job_repository,
        )

        offers = await distribution.create_offers_for_job(
            job,
            limit=5,
            expires_in_minutes=60,
        )

        sent_count = await send_job_offers_to_carriers(
            bot=self.bot,
            job=job,
            offers=offers,
            job_repository=self.job_repository,
            carrier_repository=self.carrier_repository,
        )

        if not offers:
            await escalate_job_to_manual_review(
                bot=self.bot,
                job=job,
                job_repository=self.job_repository,
            )

        return RequestSubmissionResult(
            job=job,
            offers_count=len(offers),
            sent_count=sent_count,
        )
