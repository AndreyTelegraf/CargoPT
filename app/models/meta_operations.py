from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class MetaSourceGroup(Base):
    __tablename__ = "meta_source_group"

    __table_args__ = (
        Index("ux_meta_source_group_platform_external_id", "platform", "external_id", unique=True),
        Index("ix_meta_source_group_enabled_priority", "enabled", "priority"),
        Index("ix_meta_source_group_review_status", "review_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String, nullable=False, default="facebook")
    external_id: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    canonical_url: Mapped[str] = mapped_column(String, nullable=False)
    region: Mapped[str | None] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="candidate")
    activity: Mapped[str | None] = mapped_column(String)
    ads_allowed: Mapped[str | None] = mapped_column(String)
    rules_checked: Mapped[str | None] = mapped_column(String)
    source_sheet: Mapped[str | None] = mapped_column(String)
    source_row: Mapped[int | None] = mapped_column(Integer)
    owner: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetaInboundEvent(Base):
    __tablename__ = "meta_inbound_event"

    __table_args__ = (
        Index("ux_meta_inbound_event_dedupe_key", "dedupe_key", unique=True),
        Index("ix_meta_inbound_event_status_created", "status", "created_at"),
        Index("ix_meta_inbound_event_group_id", "source_group_id"),
        Index("ix_meta_inbound_event_classification", "classification_label"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_group_id: Mapped[int | None] = mapped_column(ForeignKey("meta_source_group.id"))
    platform: Mapped[str] = mapped_column(String, nullable=False, default="facebook")
    provider_message_id: Mapped[str | None] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String, nullable=False, default="notification")
    sender: Mapped[str | None] = mapped_column(String)
    subject: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String)
    dedupe_key: Mapped[str] = mapped_column(String, nullable=False)
    classification_label: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_terms_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    draft_reply: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String)
    telegram_alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_message_refs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetaEventAction(Base):
    __tablename__ = "meta_event_action"

    __table_args__ = (Index("ix_meta_event_action_event_id_created", "event_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("meta_inbound_event.id"), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
