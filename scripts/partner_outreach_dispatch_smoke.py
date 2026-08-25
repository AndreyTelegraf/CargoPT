import asyncio
from datetime import UTC
from datetime import datetime
from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.base import Base
import app.models
from app.models.partner_outreach import PartnerOutreachComplianceSnapshot
from app.models.partner_outreach import PartnerProspect
from app.models.partner_outreach import PartnerOutreachSuppression
from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.email.models import EmailSendResult
from app.services.partner_outreach.dispatcher import DGC_SOURCE
from app.services.partner_outreach.dispatcher import PartnerOutreachDispatcher
from app.services.partner_outreach.models import OutreachMessageStatus
from app.services.partner_outreach.models import ProspectStatus
from app.services.partner_outreach.service import PartnerOutreachService


NOW = datetime(2026, 8, 11, 10, 0, tzinfo=UTC)


class FakeTransport:
    def __init__(self) -> None:
        self.messages = []

    async def send(self, message):
        self.messages.append(message)
        return EmailSendResult(provider_message_id="partner-provider-1")


async def seed(sessions):
    async with sessions() as session:
        prospect = PartnerProspect(
            company_name="Lisbon Homes",
            legal_entity_name="Lisbon Homes Lda",
            nif="509000001",
            company_domain="lisbonhomes.test",
            website_url="https://lisbonhomes.test",
            contact_email="parcerias@lisbonhomes.test",
            contact_kind="role",
            category="real_estate",
            municipality="lisboa",
            region="lisbon_metro",
            language="pt",
            source_url="https://lisbonhomes.test/contactos",
            source_checked_at=NOW,
            qualification_note="serves international buyers",
            status=ProspectStatus.CANDIDATE.value,
            approved_at=None,
            approved_by=None,
            do_not_contact=False,
            do_not_contact_reason=None,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(prospect)
        session.add(
            PartnerOutreachComplianceSnapshot(
                source=DGC_SOURCE,
                checksum_sha256="0" * 64,
                row_count=0,
                checked_at=NOW,
                imported_at=NOW,
            )
        )
        await session.flush()
        service = PartnerOutreachService(
            PartnerOutreachRepository(session),
            public_base_url="https://cargopt.pt",
            sender_signature="Equipa CargoPT",
            legal_identity="CargoPT Test Lda",
        )
        draft = await service.create_draft(prospect_id=prospect.id, now=NOW)
        approved = await service.approve_draft(
            message_id=draft.id,
            actor="smoke-reviewer",
            now=NOW,
        )
        await session.commit()
        return prospect.id, approved.id


async def main() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    prospect_id, message_id = await seed(sessions)
    transport = FakeTransport()
    dispatcher = PartnerOutreachDispatcher(
        session_maker=sessions,
        transport=transport,
        enabled=True,
        from_name="CargoPT",
        from_address="hello@cargopt.pt",
        reply_to="hello@cargopt.pt",
        daily_limit=50,
        min_interval_minutes=1,
        compliance_max_age_days=35,
        source_max_age_days=90,
        max_attempts=3,
        retry_base_seconds=1,
    )

    processed, reason = await dispatcher.dispatch_due(now=NOW, dry_run=True)
    assert processed == 0
    assert reason.startswith("dry run")
    assert transport.messages == []

    processed, reason = await dispatcher.dispatch_due(now=NOW, dry_run=False)
    assert (processed, reason) == (1, "sent")
    assert len(transport.messages) == 1
    assert transport.messages[0].to == "parcerias@lisbonhomes.test"

    async with sessions() as session:
        prospect = await session.get(PartnerProspect, prospect_id)
        message = await session.get(app.models.PartnerOutreachMessage, message_id)
        assert prospect.status == ProspectStatus.CONTACTED.value
        assert message.status == OutreachMessageStatus.SENT.value
        assert message.provider_message_id == "partner-provider-1"

    processed, reason = await dispatcher.dispatch_due(now=NOW, dry_run=False)
    assert processed == 0
    assert reason == "minimum interval since previous outreach not reached"

    async with sessions() as session:
        blocked_prospect = PartnerProspect(
            company_name="Blocked Relocation",
            legal_entity_name="Blocked Relocation Lda",
            nif="509000002",
            company_domain="blockedrelocation.test",
            website_url="https://blockedrelocation.test",
            contact_email="info@blockedrelocation.test",
            contact_kind="role",
            category="relocation",
            municipality="cascais",
            region="lisbon_metro",
            language="en",
            source_url="https://blockedrelocation.test/contact",
            source_checked_at=NOW,
            qualification_note="relocation provider",
            status=ProspectStatus.CANDIDATE.value,
            approved_at=None,
            approved_by=None,
            do_not_contact=False,
            do_not_contact_reason=None,
            created_at=NOW,
            updated_at=NOW,
        )
        session.add(blocked_prospect)
        session.add(
            PartnerOutreachSuppression(
                kind="domain",
                normalized_value="blockedrelocation.test",
                source=DGC_SOURCE,
                reason="DGC opposition list",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await session.flush()
        service = PartnerOutreachService(
            PartnerOutreachRepository(session),
            public_base_url="https://cargopt.pt",
            sender_signature="Equipa CargoPT",
            legal_identity="CargoPT Test Lda",
        )
        blocked_draft = await service.create_draft(
            prospect_id=blocked_prospect.id,
            now=NOW,
        )
        await service.approve_draft(
            message_id=blocked_draft.id,
            actor="smoke-reviewer",
            now=NOW,
        )
        blocked_prospect_id = blocked_prospect.id
        blocked_message_id = blocked_draft.id
        await session.commit()

    later = NOW + timedelta(minutes=2)
    processed, reason = await dispatcher.dispatch_due(now=later, dry_run=False)
    assert processed == 0
    assert reason == "blocked: DGC opposition list"
    assert len(transport.messages) == 1
    async with sessions() as session:
        blocked_prospect = await session.get(
            PartnerProspect,
            blocked_prospect_id,
        )
        blocked_message = await session.get(
            app.models.PartnerOutreachMessage,
            blocked_message_id,
        )
        assert blocked_prospect.do_not_contact is True
        assert blocked_message.status == OutreachMessageStatus.BLOCKED.value

    processed, reason = await dispatcher.dispatch_due(
        now=later,
        dry_run=False,
    )
    assert processed == 0
    assert reason == "no approved message is due"

    await engine.dispose()
    print("PARTNER_OUTREACH_APPROVAL_AND_DRY_RUN_OK")
    print("PARTNER_OUTREACH_DISPATCH_GUARDS_OK")


asyncio.run(main())
