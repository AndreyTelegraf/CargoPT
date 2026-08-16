"""add international address fields

Revision ID: 20260816_1200_international
Revises: 20260815_1200_carrier_locale
"""

from alembic import op
import sqlalchemy as sa


revision: str = "20260816_1200_international"
down_revision: str | None = "20260815_1200_carrier_locale"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "job_address",
        sa.Column("country_code", sa.String(length=2), nullable=True),
    )
    op.add_column(
        "job_address",
        sa.Column("address_details", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_job_address_country_code",
        "job_address",
        ["country_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_job_address_country_code", table_name="job_address")
    op.drop_column("job_address", "address_details")
    op.drop_column("job_address", "country_code")
