#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

JOB_STATUS_PATH = PROJECT_ROOT / "app/domain/job_status.py"
OFFER_STATUS_PATH = PROJECT_ROOT / "app/domain/job_offer_status.py"

FRONTEND_PATHS = {
    "track_js": PROJECT_ROOT / "app/static/assets/js/track.js",
    "workspace_js": (
        PROJECT_ROOT
        / "app/static/assets/js/tracking-workspace.js"
    ),
    "progress_header_js": (
        PROJECT_ROOT
        / "app/static/assets/js/progress-header.js"
    ),
}

NON_PUBLIC_JOB_STATUSES = {
    "draft",
    "unmatched",
}

IMPLICIT_FRONTEND_FALLBACK_STATUSES = {
    "manual_review_required",
}

SMOKE_TESTS = [
    "scripts/job_tracking_state_cards_smoke.py",
    "scripts/job_tracking_workspace_v2_smoke.py",
    "scripts/job_tracking_progress_header_smoke.py",
    "scripts/tracking_locale_parity_smoke.py",
    "scripts/job_unmatched_status_split_smoke.py",
    "scripts/job_tracking_offer_select_smoke.py",
    "scripts/job_tracking_assignment_actions_smoke.py",
]


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace(
        "+00:00",
        "Z",
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the CargoPT tracking status contract matrix "
            "and execute its static smoke suite."
        )
    )
    parser.add_argument(
        "output_directory",
        type=Path,
    )
    return parser.parse_args()


def atomic_write_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def parse_string_enum(
    path: Path,
    class_name: str,
) -> list[str]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue

        if node.name != class_name:
            continue

        values: list[str] = []

        for statement in node.body:
            if not isinstance(statement, ast.Assign):
                continue

            if len(statement.targets) != 1:
                continue

            target = statement.targets[0]

            if not isinstance(target, ast.Name):
                continue

            if not isinstance(statement.value, ast.Constant):
                continue

            if not isinstance(statement.value.value, str):
                continue

            values.append(statement.value.value)

        if not values:
            raise RuntimeError(
                f"{class_name} contains no string values"
            )

        return values

    raise RuntimeError(
        f"{class_name} was not found in {path}"
    )


def contains_status_literal(
    source: str,
    status: str,
) -> bool:
    quoted_literal = (
        rf"""["']{re.escape(status)}["']"""
    )
    bare_object_key = (
        rf"""(?<![\w$]){re.escape(status)}\s*:"""
    )

    return bool(
        re.search(
            rf"(?:{quoted_literal}|{bare_object_key})",
            source,
        )
    )


def run_smoke_test(relative_path: str) -> dict[str, Any]:
    path = PROJECT_ROOT / relative_path
    started = time.monotonic()

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    environment.setdefault(
        "BOT_TOKEN",
        "123456:TESTTOKEN",
    )
    environment.setdefault(
        "DATABASE_URL",
        "sqlite+aiosqlite:///data/cargopt_dev.db",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(path),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    return {
        "path": relative_path,
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "duration_seconds": round(
            time.monotonic() - started,
            3,
        ),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    arguments = parse_arguments()
    output_directory = arguments.output_directory.resolve()

    started_at = utc_now()
    started_monotonic = time.monotonic()

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path = output_directory / "results.json"

    issues: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    job_statuses = parse_string_enum(
        JOB_STATUS_PATH,
        "JobStatus",
    )
    offer_statuses = parse_string_enum(
        OFFER_STATUS_PATH,
        "JobOfferStatus",
    )

    unknown_non_public = sorted(
        NON_PUBLIC_JOB_STATUSES
        - set(job_statuses)
    )

    if unknown_non_public:
        issues.append(
            {
                "code": "invalid_non_public_status_contract",
                "statuses": unknown_non_public,
            }
        )

    frontend_sources = {
        key: path.read_text(encoding="utf-8")
        for key, path in FRONTEND_PATHS.items()
    }

    coverage: dict[str, dict[str, Any]] = {}

    for status in job_statuses:
        component_coverage = {
            key: contains_status_literal(
                source,
                status,
            )
            for key, source in frontend_sources.items()
        }

        explicit_components = [
            key
            for key, covered
            in component_coverage.items()
            if covered
        ]

        if status in NON_PUBLIC_JOB_STATUSES:
            coverage_mode = "explicit_non_public"
        elif (
            status
            in IMPLICIT_FRONTEND_FALLBACK_STATUSES
            and not component_coverage["track_js"]
            and not component_coverage["workspace_js"]
            and component_coverage["progress_header_js"]
        ):
            coverage_mode = "implicit_frontend_fallback"

            warnings.append(
                {
                    "code": (
                        "public_status_uses_implicit_"
                        "frontend_fallback"
                    ),
                    "status": status,
                    "missing_components": [
                        "track_js",
                        "workspace_js",
                    ],
                }
            )
        else:
            coverage_mode = "explicit_public"

        coverage[status] = {
            **component_coverage,
            "explicit_components": explicit_components,
            "coverage_mode": coverage_mode,
        }

        if not explicit_components:
            issues.append(
                {
                    "code": "backend_status_missing_from_frontend",
                    "status": status,
                }
            )

        if (
            status not in NON_PUBLIC_JOB_STATUSES
            and not component_coverage["progress_header_js"]
        ):
            issues.append(
                {
                    "code": (
                        "public_status_missing_"
                        "progress_contract"
                    ),
                    "status": status,
                }
            )

        if (
            status not in NON_PUBLIC_JOB_STATUSES
            and status
            not in IMPLICIT_FRONTEND_FALLBACK_STATUSES
            and not component_coverage["track_js"]
        ):
            issues.append(
                {
                    "code": (
                        "public_status_missing_"
                        "track_mapping"
                    ),
                    "status": status,
                }
            )

        if (
            status not in NON_PUBLIC_JOB_STATUSES
            and status
            not in IMPLICIT_FRONTEND_FALLBACK_STATUSES
            and not component_coverage["workspace_js"]
        ):
            issues.append(
                {
                    "code": (
                        "public_status_missing_"
                        "workspace_mapping"
                    ),
                    "status": status,
                }
            )

    track_js = frontend_sources["track_js"]
    workspace_js = frontend_sources["workspace_js"]
    progress_js = frontend_sources["progress_header_js"]

    action_contracts = {
        "offer_selection_only_when_offered": (
            'entry.tracking_snapshot?.status === "offered"'
            in workspace_js
        ),
        "assignment_failure_guard_present": (
            '"assigned_pending_confirmation", "assigned"'
            in workspace_js
        ),
        "offer_selection_handler_present": (
            "onSelectOffer" in workspace_js
            and "selectOffer" in track_js
        ),
        "assignment_action_handler_present": (
            "onAssignmentAction" in workspace_js
            and "sendAssignmentAction" in track_js
        ),
    }

    for contract, passed in action_contracts.items():
        if not passed:
            issues.append(
                {
                    "code": "missing_action_contract",
                    "contract": contract,
                }
            )

    fallback_contracts = {
        "track_unknown_dot_falls_back_to_searching": (
            'return "searching";' in track_js
        ),
        "track_unknown_label_falls_back_to_waiting": (
            "return messages.waitingOffers;" in track_js
        ),
        "workspace_unknown_visual_falls_back_to_completed": (
            'return "completed";' in workspace_js
        ),
        "progress_unknown_falls_back_to_received": (
            "activeIndex: 0" in progress_js
        ),
    }

    if fallback_contracts[
        "workspace_unknown_visual_falls_back_to_completed"
    ]:
        warnings.append(
            {
                "code": (
                    "unknown_status_visual_fallback_"
                    "is_completed"
                ),
                "component": "workspace_js",
                "current_fallback": "completed",
            }
        )

    smoke_results = [
        run_smoke_test(path)
        for path in SMOKE_TESTS
    ]

    for smoke in smoke_results:
        if smoke["passed"]:
            continue

        issues.append(
            {
                "code": "tracking_smoke_failed",
                "path": smoke["path"],
                "exit_code": smoke["exit_code"],
            }
        )

    status = "passed" if not issues else "failed"

    result: dict[str, Any] = {
        "collector": "tracking-status-matrix",
        "status": status,
        "started_at": started_at,
        "finished_at": utc_now(),
        "duration_seconds": round(
            time.monotonic() - started_monotonic,
            3,
        ),
        "production_access": "none",
        "production_writes": False,
        "job_statuses": job_statuses,
        "offer_statuses": offer_statuses,
        "non_public_job_statuses": sorted(
            NON_PUBLIC_JOB_STATUSES
        ),
        "public_job_statuses": [
            status_value
            for status_value in job_statuses
            if status_value
            not in NON_PUBLIC_JOB_STATUSES
        ],
        "implicit_frontend_fallback_statuses": sorted(
            IMPLICIT_FRONTEND_FALLBACK_STATUSES
        ),
        "coverage": coverage,
        "action_contracts": action_contracts,
        "fallback_contracts": fallback_contracts,
        "smoke_tests": smoke_results,
        "summary": {
            "job_status_count": len(job_statuses),
            "offer_status_count": len(offer_statuses),
            "smoke_test_count": len(smoke_results),
            "smoke_tests_passed": sum(
                1
                for smoke in smoke_results
                if smoke["passed"]
            ),
            "issue_count": len(issues),
            "warning_count": len(warnings),
        },
        "issues": issues,
        "warnings": warnings,
    }

    atomic_write_json(result_path, result)

    print(
        "JOB_STATUSES="
        + ",".join(job_statuses)
    )
    print(
        "OFFER_STATUSES="
        + ",".join(offer_statuses)
    )
    print(
        "SMOKE_TESTS_PASSED="
        f"{result['summary']['smoke_tests_passed']}"
        f"/{result['summary']['smoke_test_count']}"
    )
    print(
        f"ISSUES={len(issues)}"
    )
    print(
        f"WARNINGS={len(warnings)}"
    )
    print(
        f"RESULTS={result_path}"
    )
    print(
        "TRACKING_STATUS_MATRIX_STATUS="
        + status
    )

    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
