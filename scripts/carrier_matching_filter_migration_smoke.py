import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_REVISION = "20260915_1700_urgent_survey_reports"
CURRENT_REVISION = "20260922_1200_carrier_matching_filter"


def run_alembic(env: dict[str, str], *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=ROOT,
        env=env,
        check=True,
    )


def table_names(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="cargopt-carrier-filter-migration-"
    ) as temporary:
        database = Path(temporary) / "migration.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///{database}"
        env["BOT_TOKEN"] = "migration-smoke"

        run_alembic(env, "upgrade", "head")
        assert "carrier_matching_filter" in table_names(database)
        with sqlite3.connect(database) as connection:
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(carrier_matching_filter)"
                )
            }
            assert {
                "carrier_id",
                "max_job_volume_m3",
                "require_known_volume",
                "no_loaders_only",
                "created_at",
                "updated_at",
            } == columns
            revision = connection.execute(
                "SELECT version_num FROM alembic_version"
            ).fetchone()[0]
            assert revision == CURRENT_REVISION

        run_alembic(env, "downgrade", PREVIOUS_REVISION)
        assert "carrier_matching_filter" not in table_names(database)

    print("CARRIER_MATCHING_FILTER_MIGRATION_SMOKE_OK")


if __name__ == "__main__":
    main()
