import argparse
import hashlib
import os
import sqlite3
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path


BACKUP_PREFIX = "cargopt_prod_"
BACKUP_SUFFIX = ".sqlite3"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup(path: Path) -> None:
    uri = f"file:{path.resolve()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()
    if result != ("ok",):
        raise RuntimeError(f"SQLite quick_check failed for {path}: {result}")


def create_online_backup(
    *,
    database: Path,
    output_directory: Path,
    now: datetime | None = None,
) -> Path:
    database = database.resolve()
    output_directory = output_directory.resolve()

    if not database.is_file():
        raise FileNotFoundError(f"database not found: {database}")

    output_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    timestamp = (now or datetime.now(UTC)).astimezone(UTC)
    filename = timestamp.strftime(f"{BACKUP_PREFIX}%Y%m%dT%H%M%SZ{BACKUP_SUFFIX}")
    destination = output_directory / filename
    temporary = output_directory / f".{filename}.{os.getpid()}.tmp"

    if destination.exists():
        verify_backup(destination)
        return destination

    source_uri = f"file:{database}?mode=ro"
    try:
        with sqlite3.connect(source_uri, uri=True) as source:
            with sqlite3.connect(temporary) as target:
                source.backup(target)
                target.commit()
        verify_backup(temporary)
        temporary.chmod(0o600)
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)

    checksum_path = destination.with_suffix(destination.suffix + ".sha256")
    checksum_path.write_text(
        f"{_sha256(destination)}  {destination.name}\n",
        encoding="utf-8",
    )
    checksum_path.chmod(0o600)
    return destination


def prune_old_backups(
    *,
    output_directory: Path,
    retention_days: int,
    now: datetime | None = None,
) -> list[Path]:
    if retention_days < 1:
        raise ValueError("retention_days must be positive")

    cutoff = (now or datetime.now(UTC)).astimezone(UTC) - timedelta(
        days=retention_days
    )
    removed: list[Path] = []

    for path in sorted(output_directory.glob(f"{BACKUP_PREFIX}*{BACKUP_SUFFIX}")):
        try:
            timestamp_text = path.name.removeprefix(BACKUP_PREFIX).removesuffix(
                BACKUP_SUFFIX
            )
            created_at = datetime.strptime(
                timestamp_text,
                "%Y%m%dT%H%M%SZ",
            ).replace(tzinfo=UTC)
        except ValueError:
            continue

        if created_at >= cutoff:
            continue

        checksum_path = path.with_suffix(path.suffix + ".sha256")
        path.unlink()
        checksum_path.unlink(missing_ok=True)
        removed.append(path)

    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and verify an online CargoPT SQLite backup.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/cargopt_prod.db"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/var/lib/cargopt-backups"),
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    backup = create_online_backup(
        database=args.database,
        output_directory=args.output_dir,
    )
    removed = prune_old_backups(
        output_directory=args.output_dir,
        retention_days=args.retention_days,
    )
    print("CARGOPT_SQLITE_BACKUP_OK")
    print(f"backup={backup}")
    print(f"bytes={backup.stat().st_size}")
    print(f"sha256={_sha256(backup)}")
    print(f"pruned={len(removed)}")


if __name__ == "__main__":
    main()
