"""add job tracking token"""

from __future__ import annotations

import secrets

from alembic import op
import sqlalchemy as sa


revision = "20260705_1458_job_tracking_token"
down_revision = "20260628_1515_job_public_identity"
branch_labels = None
depends_on = None


def _columns(table_name: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.exec_driver_sql(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _indexes(table_name: str) -> set[str]:
    bind = op.get_bind()
    rows = bind.exec_driver_sql(f"PRAGMA index_list({table_name})").fetchall()
    return {row[1] for row in rows}


def _generate_token() -> str:
    return secrets.token_urlsafe(30)


def upgrade() -> None:
    bind = op.get_bind()

    if "tracking_token" not in _columns("job"):
        with op.batch_alter_table("job") as batch_op:
            batch_op.add_column(sa.Column("tracking_token", sa.String(), nullable=True))

    rows = bind.exec_driver_sql(
        "SELECT id FROM job WHERE tracking_token IS NULL OR length(tracking_token) = 0"
    ).fetchall()

    used_tokens = {
        row[0]
        for row in bind.exec_driver_sql(
            "SELECT tracking_token FROM job WHERE tracking_token IS NOT NULL AND length(tracking_token) > 0"
        ).fetchall()
    }

    for row in rows:
        job_id = row[0]
        token = _generate_token()
        while token in used_tokens:
            token = _generate_token()
        used_tokens.add(token)
        bind.exec_driver_sql(
            "UPDATE job SET tracking_token = ? WHERE id = ?",
            (token, job_id),
        )

    if "ix_job_tracking_token" not in _indexes("job"):
        op.create_index(
            "ix_job_tracking_token",
            "job",
            ["tracking_token"],
            unique=True,
        )


def downgrade() -> None:
    if "ix_job_tracking_token" in _indexes("job"):
        op.drop_index("ix_job_tracking_token", table_name="job")

    if "tracking_token" in _columns("job"):
        with op.batch_alter_table("job") as batch_op:
            batch_op.drop_column("tracking_token")
