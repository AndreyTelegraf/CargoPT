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


class CarrierCompany(Base):
    __tablename__ = "carrier_company"

    __table_args__ = (
        Index("ix_carrier_company_telegram_user_id", "telegram_user_id"),
        Index("ix_carrier_company_status", "status"),
        Index("ix_carrier_company_paid_until", "paid_until"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    company_name: Mapped[str] = mapped_column(String, nullable=False)
    public_name: Mapped[str | None] = mapped_column(String)
    contact_name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)

    telegram_user_id: Mapped[int | None] = mapped_column(
        Integer,
        unique=True,
    )
    telegram_username: Mapped[str | None] = mapped_column(String)
    preferred_locale: Mapped[str | None] = mapped_column(String(8))

    status: Mapped[str] = mapped_column(String, nullable=False)

    paid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assembly_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    packing_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    operating_regions: Mapped[str | None] = mapped_column(Text)
    experience_since_year: Mapped[int | None] = mapped_column(Integer)
    logo_file_name: Mapped[str | None] = mapped_column(String)
    publication_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    public_profile_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    profile_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    current_profile_step: Mapped[str | None] = mapped_column(String)

    internal_note: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    vehicles = relationship("CarrierVehicle", back_populates="carrier")
    invite_tokens = relationship("AdminInviteToken", back_populates="carrier")


class CarrierVehicle(Base):
    __tablename__ = "carrier_vehicle"

    __table_args__ = (
        Index("ix_carrier_vehicle_carrier_id", "carrier_id"),
        Index("ix_carrier_vehicle_is_active", "is_active"),
        Index("ix_carrier_vehicle_vehicle_type", "vehicle_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    carrier_id: Mapped[int] = mapped_column(
        ForeignKey("carrier_company.id"),
        nullable=False,
    )

    vehicle_type: Mapped[str] = mapped_column(String, nullable=False)

    payload_kg: Mapped[int | None] = mapped_column(Integer)
    volume_m3: Mapped[float | None] = mapped_column(Float)
    max_loaders: Mapped[int | None] = mapped_column(Integer)

    has_tail_lift: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_crane: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    has_mobile_lift: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    mobile_lift_max_floor: Mapped[int | None] = mapped_column(Integer)
    mobile_lift_max_weight_kg: Mapped[int | None] = mapped_column(Integer)

    crane_max_weight_kg: Mapped[int | None] = mapped_column(Integer)
    crane_reach_meters: Mapped[float | None] = mapped_column(Float)

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    carrier = relationship("CarrierCompany", back_populates="vehicles")


class AdminInviteToken(Base):
    __tablename__ = "admin_invite_token"

    carrier_id: Mapped[int] = mapped_column(
        ForeignKey("carrier_company.id"),
        nullable=False,
    )

    token: Mapped[str] = mapped_column(String, primary_key=True)

    created_by_admin_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    used_by_telegram_id: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    carrier = relationship(
        "CarrierCompany",
        back_populates="invite_tokens",
    )
