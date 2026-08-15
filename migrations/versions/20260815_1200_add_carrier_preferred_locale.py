"""add carrier preferred locale

Revision ID: 20260815_1200_carrier_locale
Revises: 20260813_1500_partner_outreach
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260815_1200_carrier_locale"
down_revision: str | None = "20260813_1500_partner_outreach"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "carrier_company",
        sa.Column("preferred_locale", sa.String(length=8), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("carrier_company", "preferred_locale")
