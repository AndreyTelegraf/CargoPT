import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


with tempfile.TemporaryDirectory(prefix="partner-outreach-migration-") as tmp:
    database = Path(tmp) / "migration.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
    env["BOT_TOKEN"] = "partner-outreach-migration-smoke"
    subprocess.run(
        [str(ROOT / ".venv/bin/alembic"), "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=True,
    )
    connection = sqlite3.connect(database)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type='table'"
            )
        }
        assert {
            "partner_prospect",
            "partner_outreach_message",
            "partner_outreach_suppression",
            "partner_outreach_compliance_snapshot",
        } <= tables
        indexes = {
            row[1]: bool(row[2])
            for row in connection.execute("pragma index_list(partner_prospect)")
        }
        assert indexes["ux_partner_prospect_domain"] is True
        assert indexes["ux_partner_prospect_email"] is True
    finally:
        connection.close()

    subprocess.run(
        [
            str(ROOT / ".venv/bin/alembic"),
            "downgrade",
            "20260805_2200_meta_ops",
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    connection = sqlite3.connect(database)
    try:
        exists = connection.execute(
            "select count(*) from sqlite_master "
            "where type='table' and name='partner_prospect'"
        ).fetchone()[0]
        assert exists == 0
    finally:
        connection.close()

print("PARTNER_OUTREACH_MIGRATION_ROUNDTRIP_OK")
