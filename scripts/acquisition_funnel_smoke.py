import asyncio
import os
import shutil
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / ".tmp_acquisition_funnel_smoke"
DB_PATH = DATA_DIR / "cargopt_dev.db"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_acquisition_funnel_smoke/cargopt_dev.db"


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "acquisition-funnel-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()

    import app.models  # noqa: F401
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.api.main import app
    from app.db.base import Base
    from app.db.session import engine as app_engine

    async def create_test_schema() -> None:
        engine = create_async_engine(DATABASE_URL)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_test_schema())

    base_event = {
        "event_type": "landing_view",
        "source_locale": "pt",
        "utm_source": "Facebook",
        "utm_medium": "paid_social",
        "utm_campaign": "lisbon_test",
        "utm_content": "creative_a",
        "referrer_host": "L.FACEBOOK.COM",
        "landing_version": "landing_static_v3_acquisition",
        "error_category": "",
    }

    with TestClient(app) as client:
        for _ in range(2):
            response = client.post("/api/v1/acquisition-events", json=base_event)
            if response.status_code != 204:
                raise SystemExit(
                    f"event endpoint failed: {response.status_code} {response.text}"
                )

        validation_event = dict(base_event)
        validation_event["event_type"] = "submit_error_validation"
        validation_event["error_category"] = "contact"
        response = client.post(
            "/api/v1/acquisition-events",
            json=validation_event,
        )
        if response.status_code != 204:
            raise SystemExit(
                f"validation event failed: {response.status_code} {response.text}"
            )

        invalid_event = dict(base_event)
        invalid_event["event_type"] = "arbitrary_event"
        response = client.post("/api/v1/acquisition-events", json=invalid_event)
        if response.status_code != 422:
            raise SystemExit(
                f"unknown event was accepted: {response.status_code} {response.text}"
            )

    asyncio.run(app_engine.dispose())

    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            """
            SELECT event_type, utm_source, referrer_host, error_category, event_count
            FROM acquisition_event_daily
            ORDER BY event_type
            """
        ).fetchall()
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(acquisition_event_daily)"
            ).fetchall()
        }

    expected = [
        ("landing_view", "facebook", "l.facebook.com", "", 2),
        (
            "submit_error_validation",
            "facebook",
            "l.facebook.com",
            "contact",
            1,
        ),
    ]
    if rows != expected:
        raise SystemExit(f"unexpected daily aggregation: {rows}")
    if "fbclid" in columns:
        raise SystemExit("daily aggregate must not store click identifiers")

    shutil.rmtree(DATA_DIR)
    print("ACQUISITION_FUNNEL_SMOKE_OK")


if __name__ == "__main__":
    main()
