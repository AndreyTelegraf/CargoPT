import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "BOT_TOKEN",
    "123456:TESTTOKEN",
)
os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///data/cargopt_dev.db",
)

from app.api.main import app


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    html = (
        root / "app/static/track/index.html"
    ).read_text(encoding="utf-8")

    js = (
        root
        / "app/static/assets/js/progress-header.js"
    ).read_text(encoding="utf-8")

    css = (
        root
        / "app/static/assets/css/progress-header.css"
    ).read_text(encoding="utf-8")

    repository = (
        root / "app/repositories/job.py"
    ).read_text(encoding="utf-8")

    schemas = (
        root / "app/api/web_request_schemas.py"
    ).read_text(encoding="utf-8")

    api = (
        root / "app/api/web_requests.py"
    ).read_text(encoding="utf-8")

    assert (
        "/assets/js/progress-header.js"
        "?v=progress-stage-v4"
        in html
    )

    assert (
        "/assets/css/progress-header.css"
        "?v=progress-cancelled-stage-v5"
        in html
    )

    assert "CANCELLED_STAGE_INDEX" in js
    assert "cancelled_from_status" in js
    assert '"cancelled-complete"' in js
    assert "getCancelledActiveIndex" in js

    assert (
        ".progress-header-step-"
        "cancelled-complete"
        in css
    )

    assert (
        ".progress-header-step-"
        "cancelled-complete:not(:last-child)"
        "::after"
        in css
    )

    assert "get_cancelled_from_status" in repository
    assert "JobStatusEvent.from_status" in repository

    assert (
        "cancelled_from_status: str | None"
        in schemas
    )

    assert (
        "cancelled_from_status="
        "cancelled_from_status"
        in api
    )

    schema = (
        app.openapi()
        ["components"]
        ["schemas"]
        ["TrackingJobResponse"]
    )

    assert (
        "cancelled_from_status"
        in schema["properties"]
    )

    print("JOB_TRACKING_PROGRESS_HEADER_OK")
    print("CANCELLED_STAGE_API_STATIC_OK")
    print("CANCELLED_CONNECTOR_STATIC_OK")


if __name__ == "__main__":
    main()
