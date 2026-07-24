"""add job email notification outbox

Revision ID: 20260724_1200_email_outbox
Revises: 20260714_2115_job_status_event
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260724_1200_email_outbox"
down_revision: str | None = "20260714_2115_job_status_event"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "job_email_notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("recipient_email", sa.String(), nullable=False),
        sa.Column("source_locale", sa.String(), nullable=False),
        sa.Column("customer_name_snapshot", sa.String(), nullable=True),
        sa.Column("status_snapshot", sa.String(), nullable=False),
        sa.Column("tracking_token_snapshot", sa.String(), nullable=False),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("delivery_status", sa.String(), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_email_notification_job_id",
        "job_email_notification",
        ["job_id"],
    )
    op.create_index(
        "ix_job_email_notification_delivery_status",
        "job_email_notification",
        ["delivery_status"],
    )
    op.create_index(
        "ix_job_email_notification_next_attempt_at",
        "job_email_notification",
        ["next_attempt_at"],
    )
    op.create_index(
        "ux_job_email_notification_dedupe_key",
        "job_email_notification",
        ["dedupe_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ux_job_email_notification_dedupe_key",
        table_name="job_email_notification",
    )
    op.drop_index(
        "ix_job_email_notification_next_attempt_at",
        table_name="job_email_notification",
    )
    op.drop_index(
        "ix_job_email_notification_delivery_status",
        table_name="job_email_notification",
    )
    op.drop_index(
        "ix_job_email_notification_job_id",
        table_name="job_email_notification",
    )
    op.drop_table("job_email_notification")
