"""add partner outreach pipeline

Revision ID: 20260813_1500_partner_outreach
Revises: 20260805_2200_meta_ops
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260813_1500_partner_outreach"
down_revision: str | None = "20260805_2200_meta_ops"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "partner_prospect",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_name", sa.String(), nullable=False),
        sa.Column("legal_entity_name", sa.String(), nullable=True),
        sa.Column("nif", sa.String(), nullable=True),
        sa.Column("company_domain", sa.String(), nullable=False),
        sa.Column("website_url", sa.Text(), nullable=False),
        sa.Column("contact_email", sa.String(), nullable=False),
        sa.Column("contact_kind", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("municipality", sa.String(), nullable=False),
        sa.Column("region", sa.String(), nullable=False),
        sa.Column("language", sa.String(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("qualification_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("do_not_contact", sa.Boolean(), nullable=False),
        sa.Column("do_not_contact_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_partner_prospect_domain",
        "partner_prospect",
        ["company_domain"],
        unique=True,
    )
    op.create_index(
        "ux_partner_prospect_email",
        "partner_prospect",
        ["contact_email"],
        unique=True,
    )
    op.create_index(
        "ix_partner_prospect_status_region",
        "partner_prospect",
        ["status", "region"],
    )

    op.create_table(
        "partner_outreach_message",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "prospect_id",
            sa.Integer(),
            sa.ForeignKey("partner_prospect.id"),
            nullable=False,
        ),
        sa.Column("sequence_step", sa.Integer(), nullable=False),
        sa.Column("locale", sa.String(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=False),
        sa.Column("dedupe_key", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_message_id", sa.String(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_partner_outreach_message_dedupe",
        "partner_outreach_message",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_partner_outreach_message_due",
        "partner_outreach_message",
        ["status", "scheduled_at"],
    )
    op.create_index(
        "ix_partner_outreach_message_prospect",
        "partner_outreach_message",
        ["prospect_id", "created_at"],
    )

    op.create_table(
        "partner_outreach_suppression",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("normalized_value", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ux_partner_outreach_suppression_kind_value",
        "partner_outreach_suppression",
        ["kind", "normalized_value"],
        unique=True,
    )

    op.create_table(
        "partner_outreach_compliance_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("checksum_sha256", sa.String(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_partner_outreach_compliance_source_checked",
        "partner_outreach_compliance_snapshot",
        ["source", "checked_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_partner_outreach_compliance_source_checked",
        table_name="partner_outreach_compliance_snapshot",
    )
    op.drop_table("partner_outreach_compliance_snapshot")
    op.drop_index(
        "ux_partner_outreach_suppression_kind_value",
        table_name="partner_outreach_suppression",
    )
    op.drop_table("partner_outreach_suppression")
    op.drop_index(
        "ix_partner_outreach_message_prospect",
        table_name="partner_outreach_message",
    )
    op.drop_index(
        "ix_partner_outreach_message_due",
        table_name="partner_outreach_message",
    )
    op.drop_index(
        "ux_partner_outreach_message_dedupe",
        table_name="partner_outreach_message",
    )
    op.drop_table("partner_outreach_message")
    op.drop_index(
        "ix_partner_prospect_status_region",
        table_name="partner_prospect",
    )
    op.drop_index("ux_partner_prospect_email", table_name="partner_prospect")
    op.drop_index("ux_partner_prospect_domain", table_name="partner_prospect")
    op.drop_table("partner_prospect")
