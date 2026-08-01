import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "cleanup_empty_old_drafts.py"


with tempfile.TemporaryDirectory() as temp_dir:
    db_path = Path(temp_dir) / "drafts.sqlite3"
    with sqlite3.connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE job (
                id INTEGER PRIMARY KEY,
                status TEXT NOT NULL,
                client_telegram_username TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                draft_step TEXT
            );
            CREATE TABLE job_status_event (
                id INTEGER PRIMARY KEY,
                job_id INTEGER NOT NULL,
                from_status TEXT,
                to_status TEXT NOT NULL,
                occurred_at TEXT NOT NULL
            );
            INSERT INTO job VALUES
                (1, 'draft', 'old', '2026-01-01 00:00:00', '2026-01-02 00:00:00', 'media'),
                (2, 'draft', 'recent', datetime('now'), datetime('now'), 'pickup_address'),
                (3, 'offered', 'sent', '2026-01-01 00:00:00', '2026-01-02 00:00:00', NULL);
            """
        )

    dry_run = subprocess.run(
        [sys.executable, str(SCRIPT), "--db", str(db_path), "--days", "30"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "mode=dry-run" in dry_run.stdout
    assert "candidates=1" in dry_run.stdout
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT status FROM job WHERE id = 1").fetchone()[0] == "draft"

    applied = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--db",
            str(db_path),
            "--days",
            "30",
            "--apply",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "archived=1" in applied.stdout
    with sqlite3.connect(db_path) as connection:
        statuses = dict(connection.execute("SELECT id, status FROM job"))
        assert statuses == {1: "draft_expired", 2: "draft", 3: "offered"}
        event = connection.execute(
            "SELECT from_status, to_status FROM job_status_event WHERE job_id = 1"
        ).fetchone()
        assert event == ("draft", "draft_expired")

print("STALE_DRAFT_ARCHIVE_SMOKE_OK")
