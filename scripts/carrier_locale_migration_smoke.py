import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260813_1500_partner_outreach"
CURRENT_REVISION = "20260816_1200_international"


with tempfile.TemporaryDirectory(prefix="carrier-locale-migration-") as tmp:
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
        assert "preferred_locale" in columns
        address_columns = {
            row[1]
            for row in connection.execute("pragma table_info(job_address)")
        }
        assert {"country_code", "address_details"} <= address_columns
        revision = connection.execute(
            "select version_num from alembic_version"
        ).fetchone()[0]
        assert revision == CURRENT_REVISION
    finally:
        connection.close()

    subprocess.run(
        [str(ROOT / ".venv/bin/alembic"), "downgrade", PREVIOUS_REVISION],
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
        assert "preferred_locale" not in columns
    finally:
        connection.close()


print("CARRIER_LOCALE_MIGRATION_SMOKE_OK")
