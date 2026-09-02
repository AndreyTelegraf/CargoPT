"""add acquisition attribution and daily funnel counters

Revision ID: 20260902_1800_acquisition_funnel
Revises: 20260816_1200_international
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260902_1800_acquisition_funnel"
down_revision: str | None = "20260816_1200_international"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column("referrer_host", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "job",
        sa.Column("fbclid", sa.String(length=1024), nullable=True),
    )
    op.create_table(
        "acquisition_event_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("source_locale", sa.String(length=2), nullable=False),
        sa.Column("utm_source", sa.String(length=255), nullable=False),
        sa.Column("utm_medium", sa.String(length=255), nullable=False),
        sa.Column("utm_campaign", sa.String(length=255), nullable=False),
        sa.Column("utm_content", sa.String(length=255), nullable=False),
        sa.Column("referrer_host", sa.String(length=255), nullable=False),
        sa.Column("landing_version", sa.String(length=64), nullable=False),
        sa.Column("error_category", sa.String(length=64), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_date",
            "event_type",
            "source_locale",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            "utm_content",
            "referrer_host",
            "landing_version",
            "error_category",
            name="uq_acquisition_event_daily_dimensions",
        ),
    )
    op.create_index(
        "ix_acquisition_event_daily_date",
        "acquisition_event_daily",
        ["event_date"],
        unique=False,
    )
    op.create_index(
        "ix_acquisition_event_daily_type",
        "acquisition_event_daily",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_acquisition_event_daily_type",
        table_name="acquisition_event_daily",
    )
    op.drop_index(
        "ix_acquisition_event_daily_date",
        table_name="acquisition_event_daily",
    )
    op.drop_table("acquisition_event_daily")
    op.drop_column("job", "fbclid")
    op.drop_column("job", "referrer_host")
