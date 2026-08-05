"""add Meta Operations Console

Revision ID: 20260805_2200_meta_ops
Revises: 20260801_1500_job_lifecycle
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_2200_meta_ops"
down_revision: str | None = "20260801_1500_job_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meta_source_group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("canonical_url", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("activity", sa.String(), nullable=True),
        sa.Column("ads_allowed", sa.String(), nullable=True),
        sa.Column("rules_checked", sa.String(), nullable=True),
        sa.Column("source_sheet", sa.String(), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_meta_source_group_platform_external_id",
        "meta_source_group",
        ["platform", "external_id"],
        unique=True,
    )
    op.create_index(
        "ix_meta_source_group_enabled_priority",
        "meta_source_group",
        ["enabled", "priority"],
    )
    op.create_index(
        "ix_meta_source_group_review_status",
        "meta_source_group",
        ["review_status"],
    )

    op.create_table(
        "meta_inbound_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_group_id", sa.Integer(), sa.ForeignKey("meta_source_group.id"), nullable=True),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("sender", sa.String(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("language", sa.String(), nullable=True),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("classification_label", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("matched_terms_json", sa.Text(), nullable=False),
        sa.Column("draft_reply", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("telegram_alerted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_message_refs_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ux_meta_inbound_event_dedupe_key", "meta_inbound_event", ["dedupe_key"], unique=True)
    op.create_index("ix_meta_inbound_event_status_created", "meta_inbound_event", ["status", "created_at"])
    op.create_index("ix_meta_inbound_event_group_id", "meta_inbound_event", ["source_group_id"])
    op.create_index("ix_meta_inbound_event_classification", "meta_inbound_event", ["classification_label"])

    op.create_table(
        "meta_event_action",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("meta_inbound_event.id"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("actor", sa.String(), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_meta_event_action_event_id_created", "meta_event_action", ["event_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_meta_event_action_event_id_created", table_name="meta_event_action")
    op.drop_table("meta_event_action")
    op.drop_index("ix_meta_inbound_event_classification", table_name="meta_inbound_event")
    op.drop_index("ix_meta_inbound_event_group_id", table_name="meta_inbound_event")
    op.drop_index("ix_meta_inbound_event_status_created", table_name="meta_inbound_event")
    op.drop_index("ux_meta_inbound_event_dedupe_key", table_name="meta_inbound_event")
    op.drop_table("meta_inbound_event")
    op.drop_index("ix_meta_source_group_review_status", table_name="meta_source_group")
    op.drop_index("ix_meta_source_group_enabled_priority", table_name="meta_source_group")
    op.drop_index("ux_meta_source_group_platform_external_id", table_name="meta_source_group")
    op.drop_table("meta_source_group")
