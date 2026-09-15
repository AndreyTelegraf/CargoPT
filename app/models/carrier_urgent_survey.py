from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Index
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.base import Base


class CarrierUrgentSurvey(Base):
    __tablename__ = "carrier_urgent_survey"

    __table_args__ = (
        UniqueConstraint(
            "campaign_key",
            "carrier_id",
            name="ux_carrier_urgent_survey_campaign_carrier",
        ),
        Index("ix_carrier_urgent_survey_campaign", "campaign_key"),
        Index("ix_carrier_urgent_survey_response", "response_code"),
        Index("ix_carrier_urgent_survey_delivery", "delivery_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    campaign_key: Mapped[str] = mapped_column(String(80), nullable=False)
    carrier_id: Mapped[int] = mapped_column(
        ForeignKey("carrier_company.id"),
        nullable=False,
    )
    recipient_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    response_code: Mapped[str | None] = mapped_column(String(32))
    delivery_status: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_id: Mapped[int | None] = mapped_column(Integer)
    last_error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
