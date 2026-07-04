import sqlite3
from pathlib import Path

from app.models.job import Job


DB_PATH = Path("data/cargopt_prod.db")


def main() -> None:
    assert hasattr(Job, "tracking_token")

    conn = sqlite3.connect(DB_PATH)
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(job)").fetchall()}
        assert "tracking_token" in columns

        indexes = {row[1] for row in conn.execute("PRAGMA index_list(job)").fetchall()}
        assert "ix_job_tracking_token" in indexes

        missing = conn.execute(
            "SELECT COUNT(*) FROM job WHERE tracking_token IS NULL OR tracking_token = ''"
        ).fetchone()[0]
        assert missing == 0

        duplicate_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT tracking_token
                FROM job
                GROUP BY tracking_token
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]
        assert duplicate_rows == 0

        print("job_tracking_token_storage_ok")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
