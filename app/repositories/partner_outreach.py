from datetime import datetime

from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner_outreach import PartnerOutreachComplianceSnapshot
from app.models.partner_outreach import PartnerOutreachMessage
from app.models.partner_outreach import PartnerOutreachSuppression
from app.models.partner_outreach import PartnerProspect
from app.services.partner_outreach.models import OutreachMessageStatus


class PartnerOutreachRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_prospect(self, prospect_id: int) -> PartnerProspect | None:
        return await self.session.get(PartnerProspect, prospect_id)

    async def get_message(
        self,
        message_id: int,
    ) -> PartnerOutreachMessage | None:
        return await self.session.get(PartnerOutreachMessage, message_id)

    async def add_prospect(self, prospect: PartnerProspect) -> PartnerProspect:
        try:
            async with self.session.begin_nested():
                self.session.add(prospect)
                await self.session.flush()
            return prospect
        except IntegrityError as exc:
            raise ValueError("prospect email or domain already exists") from exc

    async def add_message(
        self,
        message: PartnerOutreachMessage,
    ) -> PartnerOutreachMessage:
        existing = await self.get_message_by_dedupe_key(message.dedupe_key)
        if existing is not None:
            return existing
        try:
            async with self.session.begin_nested():
                self.session.add(message)
                await self.session.flush()
            return message
        except IntegrityError:
            existing = await self.get_message_by_dedupe_key(message.dedupe_key)
            if existing is None:
                raise
            return existing

    async def get_message_by_dedupe_key(
        self,
        dedupe_key: str,
    ) -> PartnerOutreachMessage | None:
        result = await self.session.execute(
            select(PartnerOutreachMessage).where(
                PartnerOutreachMessage.dedupe_key == dedupe_key
            )
        )
        return result.scalar_one_or_none()

    async def list_due_message_ids(
        self,
        *,
        now: datetime,
        max_attempts: int,
        limit: int,
    ) -> list[int]:
        result = await self.session.execute(
            select(PartnerOutreachMessage.id)
            .where(
                PartnerOutreachMessage.status.in_(
                    (
                        OutreachMessageStatus.APPROVED.value,
                        OutreachMessageStatus.RETRY.value,
                    )
                )
            )
            .where(PartnerOutreachMessage.attempt_count < max_attempts)
            .where(
                or_(
                    PartnerOutreachMessage.scheduled_at.is_(None),
                    PartnerOutreachMessage.scheduled_at <= now,
                )
            )
            .where(
                or_(
                    PartnerOutreachMessage.next_attempt_at.is_(None),
                    PartnerOutreachMessage.next_attempt_at <= now,
                )
            )
            .order_by(
                PartnerOutreachMessage.scheduled_at,
                PartnerOutreachMessage.id,
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def claim_message(
        self,
        *,
        message_id: int,
        now: datetime,
        max_attempts: int,
    ) -> tuple[PartnerOutreachMessage, PartnerProspect] | None:
        message = await self.get_message(message_id)
        if message is None:
            return None
        if message.status not in {
            OutreachMessageStatus.APPROVED.value,
            OutreachMessageStatus.RETRY.value,
        }:
            return None
        if message.attempt_count >= max_attempts:
            return None
        prospect = await self.get_prospect(message.prospect_id)
        if prospect is None:
            return None
        message.status = OutreachMessageStatus.SENDING.value
        message.attempt_count += 1
        message.last_attempt_at = now
        message.next_attempt_at = None
        message.updated_at = now
        await self.session.flush()
        return message, prospect

    async def sent_count_since(self, since: datetime) -> int:
        result = await self.session.execute(
            select(func.count(PartnerOutreachMessage.id)).where(
                PartnerOutreachMessage.status
                == OutreachMessageStatus.SENT.value,
                PartnerOutreachMessage.sent_at >= since,
            )
        )
        return int(result.scalar_one())

    async def latest_sent_at(self) -> datetime | None:
        result = await self.session.execute(
            select(func.max(PartnerOutreachMessage.sent_at)).where(
                PartnerOutreachMessage.status
                == OutreachMessageStatus.SENT.value
            )
        )
        return result.scalar_one_or_none()

    async def latest_compliance_snapshot(
        self,
        source: str,
    ) -> PartnerOutreachComplianceSnapshot | None:
        result = await self.session.execute(
            select(PartnerOutreachComplianceSnapshot)
            .where(PartnerOutreachComplianceSnapshot.source == source)
            .order_by(
                PartnerOutreachComplianceSnapshot.checked_at.desc(),
                PartnerOutreachComplianceSnapshot.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def suppression_reason(
        self,
        *,
        email: str,
        domain: str,
        nif: str,
        organization: str,
    ) -> str | None:
        checks = [
            ("email", email),
            ("domain", domain),
            ("nif", nif),
            ("organization", organization),
        ]
        conditions = [
            (
                PartnerOutreachSuppression.kind == kind,
                PartnerOutreachSuppression.normalized_value == value,
            )
            for kind, value in checks
            if value
        ]
        if not conditions:
            return None
        result = await self.session.execute(
            select(PartnerOutreachSuppression).where(
                or_(*(left & right for left, right in conditions))
            )
        )
        suppression = result.scalars().first()
        if suppression is None:
            return None
        return suppression.reason or suppression.source

    async def upsert_suppression(
        self,
        suppression: PartnerOutreachSuppression,
    ) -> PartnerOutreachSuppression:
        result = await self.session.execute(
            select(PartnerOutreachSuppression).where(
                PartnerOutreachSuppression.kind == suppression.kind,
                PartnerOutreachSuppression.normalized_value
                == suppression.normalized_value,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            self.session.add(suppression)
            await self.session.flush()
            return suppression
        existing.source = suppression.source
        existing.reason = suppression.reason
        existing.updated_at = suppression.updated_at
        await self.session.flush()
        return existing
