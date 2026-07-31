"""add carrier public profile fields

Revision ID: 20260731_1200_carrier_public_profile
Revises: 20260724_1200_email_outbox
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260731_1200_carrier_public_profile"
down_revision: str | None = "20260724_1200_email_outbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("carrier_company") as batch_op:
        batch_op.add_column(sa.Column("public_name", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("experience_since_year", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "public_profile_requested_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column("logo_file_name", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "publication_consent_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("carrier_company") as batch_op:
        batch_op.drop_column("public_profile_requested_at")
        batch_op.drop_column("publication_consent_at")
        batch_op.drop_column("logo_file_name")
        batch_op.drop_column("experience_since_year")
        batch_op.drop_column("public_name")
