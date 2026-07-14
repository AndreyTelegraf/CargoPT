"""add job utm medium and content

Revision ID: 20260714_1810_job_utm_medium_content
Revises: 20260705_1458_job_tracking_token
Create Date: 2026-07-14 18:10:00+00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260714_1810_job_utm_medium_content"
down_revision = "20260705_1458_job_tracking_token"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.add_column(
            sa.Column("utm_medium", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("utm_content", sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("job") as batch_op:
        batch_op.drop_column("utm_content")
        batch_op.drop_column("utm_medium")
