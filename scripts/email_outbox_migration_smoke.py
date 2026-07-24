import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


with tempfile.TemporaryDirectory(prefix="email-migration-smoke-") as tmp:
    database = Path(tmp) / "migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
    env["BOT_TOKEN"] = "migration-smoke"

    subprocess.run(
        [str(ROOT / ".venv/bin/alembic"), "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    connection = sqlite3.connect(database)
    try:
        columns = {
            row[1]
            for row in connection.execute(
                "pragma table_info(job_email_notification)"
            )
        }
        assert {
            "job_id",
            "event_type",
            "recipient_email",
            "source_locale",
            "tracking_token_snapshot",
            "dedupe_key",
            "delivery_status",
            "attempt_count",
            "next_attempt_at",
        } <= columns

        indexes = {
            row[1]: bool(row[2])
            for row in connection.execute(
                "pragma index_list(job_email_notification)"
            )
        }
        assert indexes["ux_job_email_notification_dedupe_key"] is True
        assert "ix_job_email_notification_delivery_status" in indexes
        assert "ix_job_email_notification_next_attempt_at" in indexes
        assert "ix_job_email_notification_job_id" in indexes
    finally:
        connection.close()

    subprocess.run(
        [
            str(ROOT / ".venv/bin/alembic"),
            "downgrade",
            "20260714_2115_job_status_event",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    connection = sqlite3.connect(database)
    try:
        exists = connection.execute(
            "select count(*) from sqlite_master "
            "where type='table' and name='job_email_notification'"
        ).fetchone()[0]
        assert exists == 0
    finally:
        connection.close()

print("EMAIL_OUTBOX_MIGRATION_OK")
