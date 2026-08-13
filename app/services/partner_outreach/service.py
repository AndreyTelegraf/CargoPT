from datetime import UTC
from datetime import datetime

from app.models.partner_outreach import PartnerOutreachMessage
from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.partner_outreach.models import OutreachMessageStatus
from app.services.partner_outreach.models import ProspectStatus
from app.services.partner_outreach.policy import ALLOWED_CATEGORIES
from app.services.partner_outreach.policy import normalize_locale
from app.services.partner_outreach.templates import render_partner_outreach


class PartnerOutreachService:
    def __init__(
        self,
        repository: PartnerOutreachRepository,
        *,
        public_base_url: str,
        sender_signature: str,
        legal_identity: str,
    ) -> None:
        self.repository = repository
        self.public_base_url = public_base_url
        self.sender_signature = sender_signature
        self.legal_identity = legal_identity

    async def create_draft(
        self,
        *,
        prospect_id: int,
        now: datetime | None = None,
    ) -> PartnerOutreachMessage:
        prospect = await self.repository.get_prospect(prospect_id)
        if prospect is None:
            raise ValueError("partner prospect not found")
        if prospect.do_not_contact:
            raise ValueError("partner prospect is suppressed")
        if prospect.status in {
            ProspectStatus.CONTACTED.value,
            ProspectStatus.REPLIED.value,
            ProspectStatus.DECLINED.value,
            ProspectStatus.DISQUALIFIED.value,
        }:
            raise ValueError("partner prospect is not eligible for a draft")
        if prospect.category not in ALLOWED_CATEGORIES:
            raise ValueError("unsupported partner category")

        locale = normalize_locale(prospect.language)
        rendered = render_partner_outreach(
            locale=locale,
            company_name=prospect.company_name,
            category=prospect.category,
            prospect_id=prospect.id,
            public_base_url=self.public_base_url,
            sender_signature=self.sender_signature,
            legal_identity=self.legal_identity,
        )
        timestamp = now or datetime.now(UTC)
        message = PartnerOutreachMessage(
            prospect_id=prospect.id,
            sequence_step=1,
            locale=locale,
            subject=rendered.subject,
            text_body=rendered.text_body,
            html_body=rendered.html_body,
            dedupe_key=f"partner:{prospect.id}:initial:v1",
            status=OutreachMessageStatus.DRAFT.value,
            scheduled_at=None,
            approved_at=None,
            approved_by=None,
            attempt_count=0,
            last_attempt_at=None,
            next_attempt_at=None,
            sent_at=None,
            provider_message_id=None,
            last_error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return await self.repository.add_message(message)

    async def approve_draft(
        self,
        *,
        message_id: int,
        actor: str,
        scheduled_at: datetime | None = None,
        now: datetime | None = None,
    ) -> PartnerOutreachMessage:
        message = await self.repository.get_message(message_id)
        if message is None:
            raise ValueError("partner outreach message not found")
        if message.status != OutreachMessageStatus.DRAFT.value:
            raise ValueError("only draft messages can be approved")
        prospect = await self.repository.get_prospect(message.prospect_id)
        if prospect is None or prospect.do_not_contact:
            raise ValueError("partner prospect is unavailable or suppressed")
        reviewer = actor.strip()
        if not reviewer:
            raise ValueError("approval actor is required")

        timestamp = now or datetime.now(UTC)
        message.status = OutreachMessageStatus.APPROVED.value
        message.scheduled_at = scheduled_at or timestamp
        message.approved_at = timestamp
        message.approved_by = reviewer
        message.updated_at = timestamp
        prospect.status = ProspectStatus.QUEUED.value
        prospect.approved_at = timestamp
        prospect.approved_by = reviewer
        prospect.updated_at = timestamp
        await self.repository.session.flush()
        return message
