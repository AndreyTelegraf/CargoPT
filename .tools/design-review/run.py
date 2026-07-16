#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESIGN_REVIEW_ROOT = PROJECT_ROOT / ".tools" / "design-review"
CONFIG_PATH = DESIGN_REVIEW_ROOT / "config.json"
SCHEMA_PATH = DESIGN_REVIEW_ROOT / "finding.schema.json"
README_PATH = DESIGN_REVIEW_ROOT / "README.md"

EXPECTED_OUTPUT_ROOT = PROJECT_ROOT / ".audit" / "design-review-v1"
FULLSTACK_TMP = PROJECT_ROOT / ".tmp_fullstack_conversion_e2e"

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,80}$")
COLLECTOR_ORDER = [
    "release-audit",
    "tracking-status-matrix",
    "conversion-frontend-e2e",
    "fullstack-conversion-e2e",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def resolve_executable(value: str) -> str:
    candidate = Path(value).expanduser()

    if not candidate.is_absolute():
        located = shutil.which(value)
        if located is None:
            raise RuntimeError(f"Python executable was not found: {value}")
        candidate = Path(located)

    executable = candidate.absolute()

    if not executable.is_file():
        raise RuntimeError(
            f"Python executable does not exist: {executable}"
        )

    if not os.access(executable, os.X_OK):
        raise RuntimeError(
            f"Python executable is not executable: {executable}"
        )

    return str(executable)


def validate_contract(config: dict[str, Any]) -> None:
    if config.get("contract_version") != "1.0":
        raise RuntimeError("unsupported Design Review contract version")

    if config.get("output_root") != ".audit/design-review-v1":
        raise RuntimeError("unexpected Design Review output root")

    policies = config.get("policies", {})

    if policies.get("production_read_only") is not True:
        raise RuntimeError("production_read_only policy must remain enabled")

    if policies.get("real_customer_requests_allowed") is not False:
        raise RuntimeError("real customer requests must remain disabled")

    if policies.get("real_telegram_messages_allowed") is not False:
        raise RuntimeError("real Telegram messages must remain disabled")

    collector_ids = [
        collector.get("id")
        for collector in config.get("collectors", [])
    ]

    if collector_ids != COLLECTOR_ORDER:
        raise RuntimeError(
            "collector order or collector identifiers differ from v1 contract"
        )


def validate_output_root() -> None:
    audit_root = PROJECT_ROOT / ".audit"

    if audit_root.exists() and audit_root.is_symlink():
        raise RuntimeError(".audit must not be a symbolic link")

    if EXPECTED_OUTPUT_ROOT.exists() and EXPECTED_OUTPUT_ROOT.is_symlink():
        raise RuntimeError(
            ".audit/design-review-v1 must not be a symbolic link"
        )

    if EXPECTED_OUTPUT_ROOT.parent != audit_root:
        raise RuntimeError("Design Review output root escaped .audit")


def choose_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def collector_command(
    collector_id: str,
    collector_path: Path,
    output_directory: Path,
    python_executable: str,
    fullstack_port: int,
) -> list[str]:
    base = [
        python_executable,
        str(collector_path),
        str(output_directory),
    ]

    if collector_id == "release-audit":
        return base

    if collector_id == "tracking-status-matrix":
        return base

    if collector_id == "conversion-frontend-e2e":
        return base

    if collector_id == "fullstack-conversion-e2e":
        return [
            *base,
            ".tmp_fullstack_conversion_e2e",
            str(fullstack_port),
        ]

    raise RuntimeError(f"unsupported collector: {collector_id}")


def backup_sqlite_database(
    source: Path,
    destination: Path,
) -> str:
    if source.is_symlink():
        raise RuntimeError(
            "SQLite backup source is a symbolic link"
        )

    if destination.exists() or destination.is_symlink():
        raise RuntimeError(
            "SQLite backup destination already exists"
        )

    source_uri = source.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(
        source_uri,
        uri=True,
    ) as source_connection:
        with sqlite3.connect(
            destination
        ) as destination_connection:
            source_connection.backup(
                destination_connection
            )

    destination_uri = (
        destination.resolve().as_uri()
        + "?mode=ro&immutable=1"
    )

    with sqlite3.connect(
        destination_uri,
        uri=True,
    ) as verification_connection:
        row = verification_connection.execute(
            "PRAGMA quick_check"
        ).fetchone()

    quick_check = str(row[0]) if row else ""

    if quick_check != "ok":
        raise RuntimeError(
            "preserved SQLite database failed "
            f"quick_check: {quick_check!r}"
        )

    return quick_check


def preserve_and_remove_fullstack_tmp(
    output_directory: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "temporary_directory": relative_path(FULLSTACK_TMP),
        "database_preserved": False,
        "temporary_directory_removed": False,
    }

    if FULLSTACK_TMP.is_symlink():
        raise RuntimeError(
            "full-stack temporary directory is a symbolic link"
        )

    if not FULLSTACK_TMP.exists():
        return result

    resolved = FULLSTACK_TMP.resolve()

    if (
        resolved.parent != PROJECT_ROOT.resolve()
        or resolved.name != ".tmp_fullstack_conversion_e2e"
    ):
        raise RuntimeError(
            "full-stack temporary directory escaped project root"
        )

    database = resolved / "cargopt_e2e.db"

    if database.is_symlink():
        raise RuntimeError("full-stack database is a symbolic link")

    if database.is_file():
        preserved = output_directory / "isolated-e2e.db"
        quick_check = backup_sqlite_database(
            database,
            preserved,
        )
        result["database_preserved"] = True
        result["preserved_database"] = relative_path(preserved)
        result["database_preservation_mode"] = "sqlite_backup"
        result["database_quick_check"] = quick_check

    shutil.rmtree(resolved)
    result["temporary_directory_removed"] = True

    return result


def build_parser(collector_ids: list[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CargoPT Design Review v1 evidence collectors."
    )
    parser.add_argument(
        "--run-id",
        help=(
            "Unique run identifier. Defaults to "
            "UTC timestamp plus Git commit prefix."
        ),
    )
    parser.add_argument(
        "--collector",
        action="append",
        choices=collector_ids,
        dest="collectors",
        help=(
            "Run only this collector. May be supplied multiple times. "
            "Defaults to all collectors."
        ),
    )
    parser.add_argument(
        "--python",
        default=sys.executable,
        dest="python_executable",
        help=(
            "Python executable used for collector subprocesses. "
            "Defaults to the interpreter running this runner."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Create the run tree and manifest without executing collectors."
        ),
    )
    return parser


def main() -> int:
    config = read_json(CONFIG_PATH)
    validate_contract(config)
    validate_output_root()

    collectors_by_id = {
        collector["id"]: collector
        for collector in config["collectors"]
    }

    parser = build_parser(list(collectors_by_id))
    arguments = parser.parse_args()

    selected_ids = arguments.collectors or COLLECTOR_ORDER.copy()
    selected_ids = list(dict.fromkeys(selected_ids))

    python_executable = resolve_executable(arguments.python_executable)

    commit = git_output("rev-parse", "HEAD")
    worktree_status = git_output(
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    )

    run_id = arguments.run_id or (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{commit[:8]}"
    )

    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise RuntimeError(
            "run ID must match "
            "^[A-Za-z0-9][A-Za-z0-9._-]{2,80}$"
        )

    output_root = EXPECTED_OUTPUT_ROOT
    output_root.mkdir(parents=True, exist_ok=True)

    run_directory = output_root / run_id

    if run_directory.exists() or run_directory.is_symlink():
        raise RuntimeError(f"run directory already exists: {run_directory}")

    directories = {
        "config": run_directory / "config",
        "scenarios": run_directory / "scenarios",
        "raw": run_directory / "raw",
        "evidence": run_directory / "evidence",
        "normalized": run_directory / "normalized",
        "reports": run_directory / "reports",
    }

    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=False)

    shutil.copy2(CONFIG_PATH, directories["config"] / "config.json")
    shutil.copy2(
        SCHEMA_PATH,
        directories["config"] / "finding.schema.json",
    )
    shutil.copy2(README_PATH, directories["config"] / "README.md")

    manifest_path = run_directory / "07-run-manifest.json"
    fullstack_port = choose_local_port()

    collector_records: list[dict[str, Any]] = []

    for collector_id in COLLECTOR_ORDER:
        contract = collectors_by_id[collector_id]
        collector_path = PROJECT_ROOT / contract["path"]
        output_directory = directories["raw"] / collector_id
        output_directory.mkdir(parents=True, exist_ok=False)

        if not collector_path.is_file():
            raise RuntimeError(
                f"collector source does not exist: {collector_path}"
            )

        command = collector_command(
            collector_id,
            collector_path,
            output_directory,
            python_executable,
            fullstack_port,
        )

        collector_records.append(
            {
                "id": collector_id,
                "selected": collector_id in selected_ids,
                "required": bool(contract.get("required")),
                "kind": contract.get("kind"),
                "production_access": contract.get("production_access"),
                "source": relative_path(collector_path),
                "output_directory": relative_path(output_directory),
                "stdout": relative_path(output_directory / "stdout.log"),
                "stderr": relative_path(output_directory / "stderr.log"),
                "command": command,
                "status": (
                    "pending"
                    if collector_id in selected_ids
                    else "not_selected"
                ),
                "started_at": None,
                "finished_at": None,
                "duration_seconds": None,
                "exit_code": None,
            }
        )

    manifest: dict[str, Any] = {
        "manifest_version": "1.0",
        "contract_version": config["contract_version"],
        "run_id": run_id,
        "project": config["project"],
        "base_url": config["base_url"],
        "status": "running",
        "dry_run": bool(arguments.dry_run),
        "started_at": utc_now(),
        "finished_at": None,
        "duration_seconds": None,
        "repository": {
            "root": str(PROJECT_ROOT),
            "commit": commit,
            "dirty": bool(worktree_status),
            "worktree_status": (
                worktree_status.splitlines()
                if worktree_status
                else []
            ),
        },
        "environment": {
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "python_executable": python_executable,
            "python_version": platform.python_version(),
            "runner_pid": os.getpid(),
            "fullstack_port": fullstack_port,
        },
        "paths": {
            "run_directory": relative_path(run_directory),
            "config_snapshot": relative_path(directories["config"]),
            "raw": relative_path(directories["raw"]),
            "evidence": relative_path(directories["evidence"]),
            "normalized": relative_path(directories["normalized"]),
            "reports": relative_path(directories["reports"]),
            "manifest": relative_path(manifest_path),
        },
        "collectors": collector_records,
        "errors": [],
    }

    started_monotonic = time.monotonic()
    atomic_write_json(manifest_path, manifest)

    print(f"RUN_ID={run_id}")
    print(f"RUN_DIRECTORY={run_directory}")
    print(f"MANIFEST={manifest_path}")

    if arguments.dry_run:
        for record in collector_records:
            if record["selected"]:
                record["status"] = "planned"

        manifest["status"] = "dry_run"
        manifest["finished_at"] = utc_now()
        manifest["duration_seconds"] = round(
            time.monotonic() - started_monotonic,
            3,
        )
        atomic_write_json(manifest_path, manifest)
        print("DESIGN_REVIEW_DRY_RUN_OK")
        return 0

    runner_exit_code = 0

    try:
        for record in collector_records:
            if not record["selected"]:
                continue

            collector_id = record["id"]
            output_directory = (
                PROJECT_ROOT / record["output_directory"]
            )
            stdout_path = PROJECT_ROOT / record["stdout"]
            stderr_path = PROJECT_ROOT / record["stderr"]

            print(f"RUN_COLLECTOR={collector_id}", flush=True)

            collector_started = time.monotonic()
            record["started_at"] = utc_now()
            record["status"] = "running"
            atomic_write_json(manifest_path, manifest)

            try:
                with (
                    stdout_path.open("w", encoding="utf-8") as stdout_file,
                    stderr_path.open("w", encoding="utf-8") as stderr_file,
                ):
                    completed = subprocess.run(
                        record["command"],
                        cwd=PROJECT_ROOT,
                        text=True,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        check=False,
                    )

                record["exit_code"] = completed.returncode
                record["status"] = (
                    "passed"
                    if completed.returncode == 0
                    else "failed"
                )

            except OSError as error:
                record["exit_code"] = 127
                record["status"] = "failed"
                manifest["errors"].append(
                    {
                        "collector": collector_id,
                        "type": type(error).__name__,
                        "message": str(error),
                    }
                )

            finally:
                record["finished_at"] = utc_now()
                record["duration_seconds"] = round(
                    time.monotonic() - collector_started,
                    3,
                )

                if collector_id == "fullstack-conversion-e2e":
                    try:
                        record["cleanup"] = (
                            preserve_and_remove_fullstack_tmp(
                                output_directory
                            )
                        )
                    except Exception as error:
                        record["status"] = "failed"
                        record["cleanup"] = {
                            "error": str(error),
                        }
                        manifest["errors"].append(
                            {
                                "collector": collector_id,
                                "type": type(error).__name__,
                                "message": str(error),
                            }
                        )

                atomic_write_json(manifest_path, manifest)

            print(
                f"COLLECTOR_STATUS={collector_id}:{record['status']}",
                flush=True,
            )

            if record["status"] != "passed" and record["required"]:
                runner_exit_code = 1

        manifest["status"] = (
            "passed"
            if runner_exit_code == 0
            else "failed"
        )

    except KeyboardInterrupt:
        manifest["status"] = "interrupted"
        manifest["errors"].append(
            {
                "type": "KeyboardInterrupt",
                "message": "Design Review run interrupted by operator",
            }
        )
        runner_exit_code = 130

    except Exception as error:
        manifest["status"] = "runner_error"
        manifest["errors"].append(
            {
                "type": type(error).__name__,
                "message": str(error),
            }
        )
        runner_exit_code = 2

    finally:
        manifest["finished_at"] = utc_now()
        manifest["duration_seconds"] = round(
            time.monotonic() - started_monotonic,
            3,
        )
        atomic_write_json(manifest_path, manifest)

    print(f"DESIGN_REVIEW_STATUS={manifest['status']}")
    print(f"DESIGN_REVIEW_EXIT_CODE={runner_exit_code}")

    return runner_exit_code


if __name__ == "__main__":
    raise SystemExit(main())
