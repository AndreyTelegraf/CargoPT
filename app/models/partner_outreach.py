from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class PartnerProspect(Base):
    __tablename__ = "partner_prospect"

    __table_args__ = (
        Index("ux_partner_prospect_domain", "company_domain", unique=True),
        Index("ux_partner_prospect_email", "contact_email", unique=True),
        Index("ix_partner_prospect_status_region", "status", "region"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    legal_entity_name: Mapped[str | None] = mapped_column(String)
    nif: Mapped[str | None] = mapped_column(String)
    company_domain: Mapped[str] = mapped_column(String, nullable=False)
    website_url: Mapped[str] = mapped_column(Text, nullable=False)
    contact_email: Mapped[str] = mapped_column(String, nullable=False)
    contact_kind: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="role",
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    municipality: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="lisbon_metro",
    )
    language: Mapped[str] = mapped_column(String, nullable=False, default="pt")
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    qualification_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="candidate",
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String)
    do_not_contact: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    do_not_contact_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class PartnerOutreachMessage(Base):
    __tablename__ = "partner_outreach_message"

    __table_args__ = (
        Index(
            "ux_partner_outreach_message_dedupe",
            "dedupe_key",
            unique=True,
        ),
        Index(
            "ix_partner_outreach_message_due",
            "status",
            "scheduled_at",
        ),
        Index(
            "ix_partner_outreach_message_prospect",
            "prospect_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("partner_prospect.id"),
        nullable=False,
    )
    sequence_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    locale: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    text_body: Mapped[str] = mapped_column(Text, nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_message_id: Mapped[str | None] = mapped_column(String)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class PartnerOutreachSuppression(Base):
    __tablename__ = "partner_outreach_suppression"

    __table_args__ = (
        Index(
            "ux_partner_outreach_suppression_kind_value",
            "kind",
            "normalized_value",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    normalized_value: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class PartnerOutreachComplianceSnapshot(Base):
    __tablename__ = "partner_outreach_compliance_snapshot"

    __table_args__ = (
        Index(
            "ix_partner_outreach_compliance_source_checked",
            "source",
            "checked_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
