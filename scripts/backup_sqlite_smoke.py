import sqlite3
import tempfile
from datetime import UTC
from datetime import datetime
from pathlib import Path

from scripts.backup_sqlite import create_online_backup
from scripts.backup_sqlite import prune_old_backups
from scripts.backup_sqlite import verify_backup


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="cargopt_backup_smoke_") as tmp:
        root = Path(tmp)
        database = root / "source.db"
        backups = root / "backups"

        with sqlite3.connect(database) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
            connection.execute("INSERT INTO sample(value) VALUES ('before')")
            connection.commit()

            created_at = datetime(2026, 8, 1, 2, 15, tzinfo=UTC)
            backup = create_online_backup(
                database=database,
                output_directory=backups,
                now=created_at,
            )
            connection.execute("INSERT INTO sample(value) VALUES ('after')")
            connection.commit()

        verify_backup(backup)
        assert backup.stat().st_mode & 0o777 == 0o600
        checksum = backup.with_suffix(backup.suffix + ".sha256")
        assert checksum.is_file()

        with sqlite3.connect(f"file:{backup}?mode=ro", uri=True) as restored:
            values = [row[0] for row in restored.execute("SELECT value FROM sample")]
        assert values == ["before"]

        old_backup = create_online_backup(
            database=database,
            output_directory=backups,
            now=datetime(2026, 6, 1, 2, 15, tzinfo=UTC),
        )
        unrelated = backups / "keep-me.txt"
        unrelated.write_text("safe", encoding="utf-8")
        removed = prune_old_backups(
            output_directory=backups,
            retention_days=30,
            now=created_at,
        )
        assert [path.resolve() for path in removed] == [old_backup.resolve()]
        assert backup.exists()
        assert unrelated.exists()

    print("BACKUP_SQLITE_SMOKE_OK")


if __name__ == "__main__":
    main()
