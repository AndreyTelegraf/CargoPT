import argparse
import sqlite3
from datetime import UTC
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "cargopt_prod.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List or archive stale CargoPT request drafts without deleting data."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Archive candidates. Without this flag the command is read-only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = args.db.expanduser().resolve()
    if args.days < 1:
        raise SystemExit("--days must be at least 1")
    if not db_path.is_file():
        raise SystemExit(f"database not found: {db_path}")

    age_arg = f"-{args.days} days"
    timestamp = datetime.now(UTC).isoformat()

    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        if quick_check != "ok":
            raise SystemExit(f"database quick_check failed: {quick_check}")

        rows = connection.execute(
            """
            SELECT id, client_telegram_username, created_at, updated_at, draft_step
            FROM job
            WHERE status = 'draft'
              AND COALESCE(updated_at, created_at) < datetime('now', ?)
            ORDER BY id
            """,
            (age_arg,),
        ).fetchall()

        print("STALE_DRAFT_ARCHIVE")
        print(f"db={db_path}")
        print(f"max_age_days={args.days}")
        print(f"mode={'apply' if args.apply else 'dry-run'}")
        print(f"candidates={len(rows)}")
        for row in rows:
            print(
                "candidate "
                f"job_id={row['id']} "
                f"client={row['client_telegram_username']} "
                f"created_at={row['created_at']} "
                f"updated_at={row['updated_at']} "
                f"draft_step={row['draft_step']}"
            )

        if args.apply and rows:
            candidate_ids = [int(row["id"]) for row in rows]
            placeholders = ",".join("?" for _ in candidate_ids)
            connection.execute("BEGIN IMMEDIATE")
            connection.executemany(
                """
                INSERT INTO job_status_event (
                    job_id, from_status, to_status, occurred_at
                ) VALUES (?, 'draft', 'draft_expired', ?)
                """,
                [(job_id, timestamp) for job_id in candidate_ids],
            )
            cursor = connection.execute(
                f"""
                UPDATE job
                SET status = 'draft_expired', updated_at = ?
                WHERE status = 'draft' AND id IN ({placeholders})
                """,
                (timestamp, *candidate_ids),
            )
            if cursor.rowcount != len(candidate_ids):
                raise RuntimeError(
                    f"archive count mismatch: expected {len(candidate_ids)}, "
                    f"updated {cursor.rowcount}"
                )
            connection.commit()
            print(f"archived={cursor.rowcount}")
        else:
            print("archived=0")

    print("STALE_DRAFT_ARCHIVE_OK")


if __name__ == "__main__":
    main()
