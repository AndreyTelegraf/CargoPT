#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve()

BASE_URL = "https://cargopt.pt"

LIGHTHOUSE = (
    PROJECT_ROOT
    / ".tools/node_modules/.bin/lighthouse"
)

CHROME = (
    PROJECT_ROOT
    / ".tools/browser-audit/browsers/"
    "chromium-1228/chrome-linux64/chrome"
)

SCENARIOS = [
    {
        "id": "pt-landing",
        "url": f"{BASE_URL}/",
    },
    {
        "id": "pt-carriers",
        "url": f"{BASE_URL}/transportadores/",
    },
    {
        "id": "pt-tracking",
        "url": f"{BASE_URL}/track/",
    },
]

VIEWPORTS = [
    "mobile",
    "desktop",
]

METRIC_AUDITS = {
    "first-contentful-paint": "fcp",
    "largest-contentful-paint": "lcp",
    "cumulative-layout-shift": "cls",
    "total-blocking-time": "tbt",
    "speed-index": "speedIndex",
    "interactive": "tti",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace(
        "+00:00",
        "Z",
    )


def atomic_write_json(
    path: Path,
    value: Any,
) -> None:
    temporary = path.with_name(
        f"{path.name}.tmp"
    )

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


def validate_toolchain() -> None:
    if not LIGHTHOUSE.is_file():
        raise RuntimeError(
            f"Lighthouse executable is absent: {LIGHTHOUSE}"
        )

    if not CHROME.is_file():
        raise RuntimeError(
            f"Chromium executable is absent: {CHROME}"
        )

    version = subprocess.run(
        [
            str(LIGHTHOUSE),
            "--version",
        ],
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()

    if version != "12.8.2":
        raise RuntimeError(
            f"unexpected Lighthouse version: {version!r}"
        )


def build_command(
    url: str,
    viewport: str,
    report_path: Path,
) -> list[str]:
    command = [
        str(LIGHTHOUSE),
        url,
        "--quiet",
        "--only-categories=performance",
        "--output=json",
        f"--output-path={report_path}",
        (
            "--chrome-flags="
            "--headless "
            "--no-sandbox "
            "--disable-dev-shm-usage"
        ),
    ]

    if viewport == "desktop":
        command.append("--preset=desktop")

    return command


def audit_value(
    report: dict[str, Any],
    audit_id: str,
) -> dict[str, Any]:
    audit = report.get(
        "audits",
        {},
    ).get(
        audit_id,
        {},
    )

    return {
        "id": audit_id,
        "score": audit.get("score"),
        "numericValue": audit.get("numericValue"),
        "numericUnit": audit.get("numericUnit"),
        "displayValue": audit.get("displayValue"),
    }


def main() -> int:
    validate_toolchain()

    OUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    reports_directory = OUT / "reports"

    reports_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    started_at = utc_now()
    started_monotonic = time.monotonic()

    scenario_results: list[dict[str, Any]] = []

    for scenario in SCENARIOS:
        for viewport in VIEWPORTS:
            scenario_id = scenario["id"]
            url = scenario["url"]

            prefix = f"{scenario_id}-{viewport}"

            report_path = (
                reports_directory / f"{prefix}.json"
            )
            stdout_path = (
                reports_directory / f"{prefix}.stdout.log"
            )
            stderr_path = (
                reports_directory / f"{prefix}.stderr.log"
            )

            command = build_command(
                url,
                viewport,
                report_path,
            )

            print(
                f"RUN {scenario_id} {viewport} {url}",
                flush=True,
            )

            scenario_started = time.monotonic()

            environment = os.environ.copy()
            environment["CHROME_PATH"] = str(CHROME)

            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            stdout_path.write_text(
                completed.stdout,
                encoding="utf-8",
            )

            stderr_path.write_text(
                completed.stderr,
                encoding="utf-8",
            )

            if completed.returncode != 0:
                raise RuntimeError(
                    "Lighthouse failed for "
                    f"{scenario_id}/{viewport} "
                    f"with exit code {completed.returncode}; "
                    f"see {stderr_path}"
                )

            if not report_path.is_file():
                raise RuntimeError(
                    "Lighthouse report was not created: "
                    f"{report_path}"
                )

            report = json.loads(
                report_path.read_text(
                    encoding="utf-8"
                )
            )

            category = report.get(
                "categories",
                {},
            ).get(
                "performance",
                {},
            )

            score = category.get("score")

            if not isinstance(score, (int, float)):
                raise RuntimeError(
                    "performance score is absent for "
                    f"{scenario_id}/{viewport}"
                )

            final_url = report.get("finalUrl")

            if not isinstance(final_url, str):
                raise RuntimeError(
                    "finalUrl is absent for "
                    f"{scenario_id}/{viewport}"
                )

            metrics = {
                output_name: audit_value(
                    report,
                    audit_id,
                )
                for audit_id, output_name
                in METRIC_AUDITS.items()
            }

            scenario_results.append(
                {
                    "id": scenario_id,
                    "viewport": viewport,
                    "requestedUrl": url,
                    "finalUrl": final_url,
                    "performanceScore": score,
                    "metrics": metrics,
                    "lighthouseVersion": report.get(
                        "lighthouseVersion"
                    ),
                    "fetchTime": report.get(
                        "fetchTime"
                    ),
                    "durationSeconds": round(
                        time.monotonic()
                        - scenario_started,
                        3,
                    ),
                    "report": (
                        report_path
                        .relative_to(OUT)
                        .as_posix()
                    ),
                    "stdout": (
                        stdout_path
                        .relative_to(OUT)
                        .as_posix()
                    ),
                    "stderr": (
                        stderr_path
                        .relative_to(OUT)
                        .as_posix()
                    ),
                }
            )

    scores = [
        result["performanceScore"]
        for result in scenario_results
    ]

    summary = {
        "scenarioCount": len(scenario_results),
        "pageCount": len(SCENARIOS),
        "viewportCount": len(VIEWPORTS),
        "minimumPerformanceScore": min(scores),
        "maximumPerformanceScore": max(scores),
        "averagePerformanceScore": round(
            sum(scores) / len(scores),
            4,
        ),
        "failedScenarioCount": 0,
    }

    output = {
        "collector": "lighthouse",
        "status": "passed",
        "baseUrl": BASE_URL,
        "lighthouseVersion": "12.8.2",
        "browser": "chromium",
        "productionAccess": "read-only",
        "productionWrites": 0,
        "realRequestSubmission": False,
        "startedAt": started_at,
        "finishedAt": utc_now(),
        "durationSeconds": round(
            time.monotonic() - started_monotonic,
            3,
        ),
        "scenarios": scenario_results,
        "summary": summary,
    }

    atomic_write_json(
        OUT / "results.json",
        output,
    )

    atomic_write_json(
        OUT / "findings.json",
        [],
    )

    print()
    print(f"PAGE_SCENARIOS={summary['scenarioCount']}")
    print(
        "MINIMUM_PERFORMANCE_SCORE="
        f"{summary['minimumPerformanceScore']}"
    )
    print(
        "MAXIMUM_PERFORMANCE_SCORE="
        f"{summary['maximumPerformanceScore']}"
    )
    print(
        "AVERAGE_PERFORMANCE_SCORE="
        f"{summary['averagePerformanceScore']}"
    )
    print("FAILED_SCENARIOS=0")
    print("PRODUCTION_WRITES=0")
    print("REAL_REQUEST_SUBMISSION=false")
    print(f"OUTPUT={OUT}")
    print("LIGHTHOUSE_COLLECTOR_EXECUTION_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
