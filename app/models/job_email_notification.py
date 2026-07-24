from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class JobEmailNotification(Base):
    __tablename__ = "job_email_notification"

    __table_args__ = (
        Index("ix_job_email_notification_job_id", "job_id"),
        Index("ix_job_email_notification_delivery_status", "delivery_status"),
        Index("ix_job_email_notification_next_attempt_at", "next_attempt_at"),
        Index(
            "ux_job_email_notification_dedupe_key",
            "dedupe_key",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job.id"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    recipient_email: Mapped[str] = mapped_column(String, nullable=False)
    source_locale: Mapped[str] = mapped_column(String, nullable=False)
    customer_name_snapshot: Mapped[str | None] = mapped_column(String)
    status_snapshot: Mapped[str] = mapped_column(String, nullable=False)
    tracking_token_snapshot: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    dedupe_key: Mapped[str] = mapped_column(String, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String, nullable=False)
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
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
