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


class ClientJobLimitError(ValueError):
    pass


@dataclass(frozen=True)
class RequestSubmissionResult:
    job: Job
    offers_count: int
    sent_count: int
    queued_count: int = 0


class RequestSubmissionService:
    def __init__(
        self,
        *,
        job_repository: JobRepository,
        carrier_repository: CarrierRepository,
        bot,
        telegram_notification_service=None,
    ) -> None:
        self.job_repository = job_repository
        self.carrier_repository = carrier_repository
        self.bot = bot
        self.telegram_notification_service = telegram_notification_service

    def _require_notification_service(self):
        if self.telegram_notification_service is None:
            raise RuntimeError("telegram notification outbox service is required")
        return self.telegram_notification_service

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

        notification_service = self._require_notification_service()

        distribution = OfferDistributionService(
            matching_service=JobMatchingService(
                CarrierSearchService(self.carrier_repository)
            ),
            offer_service=JobOfferService(self.job_repository),
            job_repository=self.job_repository,
        )

        distribution_result = await distribution.create_offer_distribution_for_job(
            job,
            limit=5,
            expires_in_minutes=60,
        )
        offers = distribution_result.offers

        if offers:
            queued = await notification_service.enqueue_carrier_offers(
                job=job,
                offers=offers,
            )
            await self.job_repository.commit()
            sent_count = 0
            queued_count = len(queued)
        else:
            await escalate_job_to_manual_review(
                bot=self.bot,
                job=job,
                job_repository=self.job_repository,
                matching_reason=distribution_result.matching_reason,
                matching_regions=distribution_result.matching_regions,
                commit_before_notification=True,
                notification_service=notification_service,
            )
            sent_count = 0
            queued_count = 0

        return RequestSubmissionResult(
            job=job,
            offers_count=len(offers),
            sent_count=sent_count,
            queued_count=queued_count,
        )
