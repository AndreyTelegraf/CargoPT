import argparse
import asyncio
from datetime import UTC
from datetime import datetime

from sqlalchemy import select

from app.config import settings
from app.db.session import async_session_maker
from app.models.partner_outreach import PartnerOutreachMessage
from app.models.partner_outreach import PartnerOutreachSuppression
from app.models.partner_outreach import PartnerProspect
from app.repositories.partner_outreach import PartnerOutreachRepository
from app.services.partner_outreach.models import ProspectStatus
from app.services.partner_outreach.policy import normalize_domain
from app.services.partner_outreach.policy import normalize_email
from app.services.partner_outreach.service import PartnerOutreachService


def parse_ids(value: str) -> list[int]:
    ids = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not ids:
        raise argparse.ArgumentTypeError("at least one id is required")
    return list(dict.fromkeys(ids))


async def list_records() -> None:
    async with async_session_maker() as session:
        prospects = (
            await session.execute(
                select(PartnerProspect).order_by(PartnerProspect.id)
            )
        ).scalars()
        for prospect in prospects:
            print(
                f"PROSPECT {prospect.id} | {prospect.status} | "
                f"{prospect.company_name} | {prospect.category} | "
                f"{prospect.contact_email}"
            )
        messages = (
            await session.execute(
                select(PartnerOutreachMessage).order_by(
                    PartnerOutreachMessage.id
                )
            )
        ).scalars()
        for message in messages:
            print(
                f"MESSAGE {message.id} | prospect={message.prospect_id} | "
                f"{message.status} | {message.subject}"
            )


async def create_drafts(prospect_ids: list[int]) -> None:
    async with async_session_maker() as session:
        service = PartnerOutreachService(
            PartnerOutreachRepository(session),
            public_base_url=settings.email_public_base_url,
            sender_signature=settings.partner_outreach_sender_signature,
            legal_identity=settings.partner_outreach_legal_identity,
        )
        for prospect_id in prospect_ids:
            message = await service.create_draft(prospect_id=prospect_id)
            print(f"MESSAGE {message.id} | {message.subject}")
            print(message.text_body)
            print("---")
        await session.commit()


async def approve_messages(message_ids: list[int], actor: str) -> None:
    async with async_session_maker() as session:
        service = PartnerOutreachService(
            PartnerOutreachRepository(session),
            public_base_url=settings.email_public_base_url,
            sender_signature=settings.partner_outreach_sender_signature,
            legal_identity=settings.partner_outreach_legal_identity,
        )
        for message_id in message_ids:
            message = await service.approve_draft(
                message_id=message_id,
                actor=actor,
            )
            print(f"PARTNER_MESSAGE_APPROVED={message.id}")
        await session.commit()


async def suppress_prospect(prospect_id: int, reason: str) -> None:
    now = datetime.now(UTC)
    async with async_session_maker() as session:
        repository = PartnerOutreachRepository(session)
        prospect = await repository.get_prospect(prospect_id)
        if prospect is None:
            raise ValueError("partner prospect not found")
        for kind, value in (
            ("email", normalize_email(prospect.contact_email)),
            ("domain", normalize_domain(prospect.company_domain)),
        ):
            await repository.upsert_suppression(
                PartnerOutreachSuppression(
                    kind=kind,
                    normalized_value=value,
                    source="internal_opt_out",
                    reason=reason,
                    created_at=now,
                    updated_at=now,
                )
            )
        prospect.do_not_contact = True
        prospect.do_not_contact_reason = reason
        prospect.status = ProspectStatus.DECLINED.value
        prospect.updated_at = now
        await session.commit()
    print(f"PARTNER_PROSPECT_SUPPRESSED={prospect_id}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    draft = subparsers.add_parser("draft")
    draft.add_argument("--prospect-ids", type=parse_ids, required=True)
    approve = subparsers.add_parser("approve")
    approve.add_argument("--message-ids", type=parse_ids, required=True)
    approve.add_argument("--actor", required=True)
    suppress = subparsers.add_parser("suppress")
    suppress.add_argument("--prospect-id", type=int, required=True)
    suppress.add_argument("--reason", required=True)
    args = parser.parse_args()

    if not settings.partner_outreach_enabled:
        raise SystemExit("PARTNER_OUTREACH_DISABLED")
    if args.command == "list":
        asyncio.run(list_records())
    elif args.command == "draft":
        asyncio.run(create_drafts(args.prospect_ids))
    elif args.command == "approve":
        asyncio.run(approve_messages(args.message_ids, args.actor))
    elif args.command == "suppress":
        asyncio.run(suppress_prospect(args.prospect_id, args.reason))


if __name__ == "__main__":
    main()
