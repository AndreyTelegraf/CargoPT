"""add carrier urgent availability survey

Revision ID: 20260915_1500_carrier_urgent_survey
Revises: 20260910_1930_offer_terms
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260915_1500_carrier_urgent_survey"
down_revision: str | None = "20260910_1930_offer_terms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "carrier_urgent_survey",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campaign_key", sa.String(length=80), nullable=False),
        sa.Column("carrier_id", sa.Integer(), nullable=False),
        sa.Column("recipient_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("response_code", sa.String(length=32), nullable=True),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("provider_message_id", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["carrier_id"], ["carrier_company.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_key",
            "carrier_id",
            name="ux_carrier_urgent_survey_campaign_carrier",
        ),
    )
    op.create_index(
        "ix_carrier_urgent_survey_campaign",
        "carrier_urgent_survey",
        ["campaign_key"],
    )
    op.create_index(
        "ix_carrier_urgent_survey_response",
        "carrier_urgent_survey",
        ["response_code"],
    )
    op.create_index(
        "ix_carrier_urgent_survey_delivery",
        "carrier_urgent_survey",
        ["delivery_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_carrier_urgent_survey_delivery",
        table_name="carrier_urgent_survey",
    )
    op.drop_index(
        "ix_carrier_urgent_survey_response",
        table_name="carrier_urgent_survey",
    )
    op.drop_index(
        "ix_carrier_urgent_survey_campaign",
        table_name="carrier_urgent_survey",
    )
    op.drop_table("carrier_urgent_survey")
