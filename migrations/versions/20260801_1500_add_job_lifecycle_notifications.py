"""add job lifecycle notification and completion fields

Revision ID: 20260801_1500_job_lifecycle
Revises: 20260731_1200_carrier_public_profile
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260801_1500_job_lifecycle"
down_revision: str | None = "20260731_1200_carrier_public_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.add_column(sa.Column("draft_step", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "reminder_24h_sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "reminder_2h_sent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "completion_prompted_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column("client_completion_status", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("carrier_completion_status", sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("carrier_completion_status")
        batch_op.drop_column("client_completion_status")
        batch_op.drop_column("completion_prompted_at")
        batch_op.drop_column("reminder_2h_sent_at")
        batch_op.drop_column("reminder_24h_sent_at")
        batch_op.drop_column("draft_step")
