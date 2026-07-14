"""add job status event"""

from alembic import op
import sqlalchemy as sa

revision = "20260714_2115_job_status_event"
down_revision = "20260714_1810_job_utm_medium_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_status_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(), nullable=True),
        sa.Column("to_status", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
    )
    op.create_index("ix_job_status_event_job_id", "job_status_event", ["job_id"])
    op.create_index("ix_job_status_event_to_status", "job_status_event", ["to_status"])
    op.create_index("ix_job_status_event_occurred_at", "job_status_event", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_job_status_event_occurred_at", table_name="job_status_event")
    op.drop_index("ix_job_status_event_to_status", table_name="job_status_event")
    op.drop_index("ix_job_status_event_job_id", table_name="job_status_event")
    op.drop_table("job_status_event")
