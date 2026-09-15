"""add carrier urgent survey report events

Revision ID: 20260915_1700_urgent_survey_reports
Revises: 20260915_1500_carrier_urgent_survey
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_1700_urgent_survey_reports"
down_revision: str | None = "20260915_1500_carrier_urgent_survey"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "carrier_urgent_survey_report_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("survey_id", sa.Integer(), nullable=False),
        sa.Column("carrier_id", sa.Integer(), nullable=False),
        sa.Column("carrier_label", sa.String(length=255), nullable=False),
        sa.Column("carrier_telegram_username", sa.String(length=255), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("previous_response_code", sa.String(length=32), nullable=True),
        sa.Column("response_code", sa.String(length=32), nullable=False),
        sa.Column("report_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["carrier_id"], ["carrier_company.id"]),
        sa.ForeignKeyConstraint(["survey_id"], ["carrier_urgent_survey.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_carrier_urgent_survey_report_event_delivery",
        "carrier_urgent_survey_report_event",
        ["delivery_status"],
    )
    op.create_index(
        "ix_carrier_urgent_survey_report_event_survey",
        "carrier_urgent_survey_report_event",
        ["survey_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_carrier_urgent_survey_report_event_survey",
        table_name="carrier_urgent_survey_report_event",
    )
    op.drop_index(
        "ix_carrier_urgent_survey_report_event_delivery",
        table_name="carrier_urgent_survey_report_event",
    )
    op.drop_table("carrier_urgent_survey_report_event")
