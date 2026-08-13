import logging
from datetime import UTC
from datetime import datetime
from datetime import time
from datetime import timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.email.models import EmailMessage
from app.services.email.notification_service import recipient_domain
from app.services.email.transport import EmailTransport
from app.services.email.transport import PermanentEmailTransportError
from app.services.email.transport import TemporaryEmailTransportError
from app.services.partner_outreach.models import OutreachMessageStatus
from app.services.partner_outreach.models import ProspectStatus
from app.services.partner_outreach.policy import normalize_nif
from app.services.partner_outreach.policy import normalize_organization
from app.services.partner_outreach.policy import validate_prospect_contact


logger = logging.getLogger(__name__)
LISBON_TZ = ZoneInfo("Europe/Lisbon")
DGC_SOURCE = "dgc_legal_entities"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def within_business_window(now: datetime) -> bool:
    local_now = _as_utc(now).astimezone(LISBON_TZ)
    if local_now.weekday() >= 5:
        return False
    return time(9, 30) <= local_now.time() < time(17, 30)


class PartnerOutreachDispatcher:
    def __init__(
        self,
        *,
        session_maker: async_sessionmaker,
        transport: EmailTransport,
        enabled: bool,
        from_name: str,
        from_address: str,
        reply_to: str | None,
        daily_limit: int,
        min_interval_minutes: int,
        compliance_max_age_days: int,
        max_attempts: int,
        retry_base_seconds: int,
    ) -> None:
        self.session_maker = session_maker
        self.transport = transport
        self.enabled = enabled
        self.from_name = from_name
        self.from_address = from_address
        self.reply_to = reply_to or None
        self.daily_limit = daily_limit
        self.min_interval = timedelta(minutes=min_interval_minutes)
        self.compliance_max_age = timedelta(days=compliance_max_age_days)
        self.max_attempts = max_attempts
        self.retry_base_seconds = retry_base_seconds

    async def dispatch_due(
        self,
        *,
        now: datetime | None = None,
        dry_run: bool = True,
    ) -> tuple[int, str]:
        timestamp = _as_utc(now or datetime.now(UTC))
        if not self.enabled:
            return 0, "partner outreach sending is disabled"
        if not within_business_window(timestamp):
            return 0, "outside Lisbon business window"

        async with self.session_maker() as session:
            repository = PartnerOutreachRepository(session)
            preflight_reason = await self._preflight(repository, timestamp)
            if preflight_reason:
                return 0, preflight_reason
            due_ids = await repository.list_due_message_ids(
                now=timestamp,
                max_attempts=self.max_attempts,
                limit=1,
            )

        if not due_ids:
            return 0, "no approved message is due"
        if dry_run:
            return 0, f"dry run: message {due_ids[0]} is eligible"
        processed = await self._dispatch_one(due_ids[0], timestamp)
        return (1, "sent") if processed else (0, "message was not claimable")

    async def _preflight(
        self,
        repository: PartnerOutreachRepository,
        now: datetime,
    ) -> str | None:
        snapshot = await repository.latest_compliance_snapshot(DGC_SOURCE)
        if snapshot is None:
            return "missing DGC legal-entity suppression snapshot"
        checked_at = _as_utc(snapshot.checked_at)
        if now - checked_at > self.compliance_max_age:
            return "DGC legal-entity suppression snapshot is stale"

        local_now = now.astimezone(LISBON_TZ)
        local_midnight = datetime.combine(
            local_now.date(),
            time.min,
            tzinfo=LISBON_TZ,
        ).astimezone(UTC)
        sent_today = await repository.sent_count_since(local_midnight)
        if sent_today >= self.daily_limit:
            return "daily outreach limit reached"

        last_sent_at = await repository.latest_sent_at()
        if last_sent_at is not None:
            elapsed = now - _as_utc(last_sent_at)
            if elapsed < self.min_interval:
                return "minimum interval since previous outreach not reached"
        return None

    async def _dispatch_one(self, message_id: int, now: datetime) -> bool:
        async with self.session_maker() as session:
            repository = PartnerOutreachRepository(session)
            claimed = await repository.claim_message(
                message_id=message_id,
                now=now,
                max_attempts=self.max_attempts,
            )
            if claimed is None:
                await session.rollback()
                return False
            message, prospect = claimed

            block_reason = await self._block_reason(repository, prospect)
            if block_reason:
                message.status = OutreachMessageStatus.BLOCKED.value
                message.last_error = block_reason
                message.updated_at = now
                prospect.do_not_contact = True
                prospect.do_not_contact_reason = block_reason
                prospect.status = ProspectStatus.DISQUALIFIED.value
                prospect.updated_at = now
                await session.commit()
                logger.warning(
                    "partner_outreach_blocked",
                    extra={
                        "prospect_id": prospect.id,
                        "recipient_domain": recipient_domain(
                            prospect.contact_email
                        ),
                        "reason": block_reason,
                    },
                )
                return True

            snapshot = {
                "message_id": message.id,
                "prospect_id": prospect.id,
                "recipient_email": prospect.contact_email,
                "subject": message.subject,
                "text_body": message.text_body,
                "html_body": message.html_body,
                "attempt_count": message.attempt_count,
            }
            await session.commit()

        email = EmailMessage(
            to=snapshot["recipient_email"],
            subject=snapshot["subject"],
            text_body=snapshot["text_body"],
            html_body=snapshot["html_body"],
            from_address=self.from_address,
            from_name=self.from_name,
            reply_to=self.reply_to,
        )
        try:
            result = await self.transport.send(email)
        except PermanentEmailTransportError:
            await self._record_failure(snapshot, now=now, permanent=True)
        except TemporaryEmailTransportError:
            await self._record_failure(snapshot, now=now, permanent=False)
        except Exception:
            logger.exception(
                "partner outreach transport raised unexpected error",
                extra={
                    "prospect_id": snapshot["prospect_id"],
                    "recipient_domain": recipient_domain(
                        snapshot["recipient_email"]
                    ),
                },
            )
            await self._record_failure(snapshot, now=now, permanent=False)
        else:
            async with self.session_maker() as session:
                repository = PartnerOutreachRepository(session)
                message = await repository.get_message(snapshot["message_id"])
                prospect = await repository.get_prospect(snapshot["prospect_id"])
                if message is None or prospect is None:
                    raise RuntimeError("claimed outreach record disappeared")
                message.status = OutreachMessageStatus.SENT.value
                message.sent_at = now
                message.provider_message_id = result.provider_message_id
                message.last_error = None
                message.updated_at = now
                prospect.status = ProspectStatus.CONTACTED.value
                prospect.updated_at = now
                await session.commit()
            logger.info(
                "partner_outreach_sent",
                extra={
                    "prospect_id": snapshot["prospect_id"],
                    "recipient_domain": recipient_domain(
                        snapshot["recipient_email"]
                    ),
                },
            )
        return True

    async def _block_reason(self, repository, prospect) -> str | None:
        if prospect.do_not_contact:
            return prospect.do_not_contact_reason or "prospect is suppressed"
        if prospect.contact_kind != "role":
            return "contact is not a role-based company mailbox"
        try:
            email, domain = validate_prospect_contact(
                email=prospect.contact_email,
                website_url=prospect.website_url,
                source_url=prospect.source_url,
            )
        except ValueError as exc:
            return str(exc)
        organization = normalize_organization(
            prospect.legal_entity_name or prospect.company_name
        )
        return await repository.suppression_reason(
            email=email,
            domain=domain,
            nif=normalize_nif(prospect.nif),
            organization=organization,
        )

    async def _record_failure(
        self,
        snapshot: dict,
        *,
        now: datetime,
        permanent: bool,
    ) -> None:
        exhausted = snapshot["attempt_count"] >= self.max_attempts
        backoff = self.retry_base_seconds * (
            2 ** (snapshot["attempt_count"] - 1)
        )
        async with self.session_maker() as session:
            repository = PartnerOutreachRepository(session)
            message = await repository.get_message(snapshot["message_id"])
            if message is None:
                raise RuntimeError("claimed outreach message disappeared")
            if permanent or exhausted:
                message.status = OutreachMessageStatus.FAILED.value
                message.next_attempt_at = None
            else:
                message.status = OutreachMessageStatus.RETRY.value
                message.next_attempt_at = now + timedelta(seconds=backoff)
            message.last_error = (
                "permanent email transport failure"
                if permanent
                else "temporary email transport failure"
            )
            message.updated_at = now
            await session.commit()
