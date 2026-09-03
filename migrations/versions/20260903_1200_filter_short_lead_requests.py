"""filter short-lead requests from automatic carrier distribution

Revision ID: 20260903_1200_short_lead_filter
Revises: 20260902_1800_acquisition_funnel
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260903_1200_short_lead_filter"
down_revision: str | None = "20260902_1800_acquisition_funnel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column(
            "short_lead_time_filtered",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("job", "short_lead_time_filtered")
