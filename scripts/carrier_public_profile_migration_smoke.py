import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


with tempfile.TemporaryDirectory(prefix="carrier-profile-migration-smoke-") as tmp:
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
            for row in connection.execute("pragma table_info(carrier_company)")
        }
        assert {
            "public_name",
            "experience_since_year",
            "logo_file_name",
            "publication_consent_at",
            "public_profile_requested_at",
        } <= columns
        revision = connection.execute(
            "select version_num from alembic_version"
        ).fetchone()[0]
        assert revision == "20260731_1200_carrier_public_profile"
    finally:
        connection.close()

    subprocess.run(
        [
            str(ROOT / ".venv/bin/alembic"),
            "downgrade",
            "20260724_1200_email_outbox",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )

    connection = sqlite3.connect(database)
    try:
        columns = {
            row[1]
            for row in connection.execute("pragma table_info(carrier_company)")
        }
        assert "public_name" not in columns
        assert "experience_since_year" not in columns
        assert "logo_file_name" not in columns
        assert "publication_consent_at" not in columns
        assert "public_profile_requested_at" not in columns
    finally:
        connection.close()


print("CARRIER_PUBLIC_PROFILE_MIGRATION_OK")
