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
from sqlalchemy.orm import relationship

from app.db.base import Base


class Job(Base):
    __tablename__ = "job"

    __table_args__ = (
        Index("ix_job_status", "status"),
        Index("ix_job_client_telegram_user_id", "client_telegram_user_id"),
        Index("ix_job_requested_date", "requested_date"),
        Index("ix_job_tracking_token", "tracking_token", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tracking_token: Mapped[str | None] = mapped_column(String)

    client_telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    client_telegram_username: Mapped[str | None] = mapped_column(String)

    source: Mapped[str | None] = mapped_column(String)
    source_locale: Mapped[str | None] = mapped_column(String)

    customer_name: Mapped[str | None] = mapped_column(String)
    customer_email: Mapped[str | None] = mapped_column(String)
    preferred_contact: Mapped[str | None] = mapped_column(String)

    client_phone: Mapped[str | None] = mapped_column(String)
    client_whatsapp: Mapped[str | None] = mapped_column(String)

    utm_source: Mapped[str | None] = mapped_column(String)
    utm_medium: Mapped[str | None] = mapped_column(String)
    utm_campaign: Mapped[str | None] = mapped_column(String)
    utm_content: Mapped[str | None] = mapped_column(String)
    landing_version: Mapped[str | None] = mapped_column(String)

    status: Mapped[str] = mapped_column(String, nullable=False)

    requested_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    client_confirmation_status: Mapped[str | None] = mapped_column(String)
    carrier_confirmation_status: Mapped[str | None] = mapped_column(String)

    needs_assembly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_packing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    needs_tail_lift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_crane: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_mobile_lift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    required_loaders: Mapped[int | None] = mapped_column(Integer)

    estimated_payload_kg: Mapped[int | None] = mapped_column(Integer)
    estimated_volume_m3: Mapped[float | None] = mapped_column(Float)

    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    addresses = relationship("JobAddress", back_populates="job")
    items = relationship("JobItem", back_populates="job")
    media = relationship("JobMedia", back_populates="job")


class JobStatusEvent(Base):
    __tablename__ = "job_status_event"

    __table_args__ = (
        Index("ix_job_status_event_job_id", "job_id"),
        Index("ix_job_status_event_to_status", "to_status"),
        Index("ix_job_status_event_occurred_at", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job.id"),
        nullable=False,
    )
    from_status: Mapped[str | None] = mapped_column(String)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class JobAddress(Base):
    __tablename__ = "job_address"

    __table_args__ = (
        Index("ix_job_address_job_id", "job_id"),
        Index("ix_job_address_kind", "kind"),
        Index("ix_job_address_city", "city"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), nullable=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)

    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_google_maps_url: Mapped[str | None] = mapped_column(Text)
    normalized_address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String)
    postal_code: Mapped[str | None] = mapped_column(String)

    floor: Mapped[int | None] = mapped_column(Integer)
    has_elevator: Mapped[bool | None] = mapped_column(Boolean)

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    map_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("Job", back_populates="addresses")



class JobMedia(Base):
    __tablename__ = "job_media"

    __table_args__ = (
        Index("ix_job_media_job_id", "job_id"),
        Index("ix_job_media_media_type", "media_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), nullable=False)

    media_type: Mapped[str] = mapped_column(String, nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("Job", back_populates="media")


class JobItem(Base):
    __tablename__ = "job_item"

    __table_args__ = (
        Index("ix_job_item_job_id", "job_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int | None] = mapped_column(Integer)
    estimated_weight_kg: Mapped[int | None] = mapped_column(Integer)
    estimated_volume_m3: Mapped[float | None] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    job = relationship("Job", back_populates="items")


class JobOffer(Base):
    __tablename__ = "job_offer"

    __table_args__ = (
        Index("ix_job_offer_job_id", "job_id"),
        Index("ix_job_offer_carrier_id", "carrier_id"),
        Index("ix_job_offer_vehicle_id", "vehicle_id"),
        Index("ix_job_offer_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    job_id: Mapped[int] = mapped_column(ForeignKey("job.id"), nullable=False)
    carrier_id: Mapped[int] = mapped_column(ForeignKey("carrier_company.id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("carrier_vehicle.id"), nullable=False)

    status: Mapped[str] = mapped_column(String, nullable=False)

    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    carrier_note: Mapped[str | None] = mapped_column(Text)
    decline_reason: Mapped[str | None] = mapped_column(String)
    price_cents: Mapped[int | None] = mapped_column(Integer)

    carrier_message_chat_id: Mapped[int | None] = mapped_column(Integer)
    carrier_message_id: Mapped[int | None] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ClientBan(Base):
    __tablename__ = "client_ban"

    __table_args__ = (
        Index("ix_client_ban_telegram_user_id", "telegram_user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String)
    reason: Mapped[str | None] = mapped_column(Text)
    banned_by_admin_id: Mapped[int] = mapped_column(Integer, nullable=False)
    banned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    unbanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unbanned_by_admin_id: Mapped[int | None] = mapped_column(Integer)
