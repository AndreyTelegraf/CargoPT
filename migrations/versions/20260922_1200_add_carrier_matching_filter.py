"""add per-carrier matching filters

Revision ID: 20260922_1200_carrier_matching_filter
Revises: 20260915_1700_urgent_survey_reports
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260922_1200_carrier_matching_filter"
down_revision: str | None = "20260915_1700_urgent_survey_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "carrier_matching_filter",
        sa.Column("carrier_id", sa.Integer(), nullable=False),
        sa.Column("max_job_volume_m3", sa.Float(), nullable=True),
        sa.Column("require_known_volume", sa.Boolean(), nullable=False),
        sa.Column("no_loaders_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["carrier_id"], ["carrier_company.id"]),
        sa.PrimaryKeyConstraint("carrier_id"),
    )


def downgrade() -> None:
    op.drop_table("carrier_matching_filter")
