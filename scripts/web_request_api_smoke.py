import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / ".tmp_web_request_api_smoke"
DATABASE_URL = "sqlite+aiosqlite:///.tmp_web_request_api_smoke/cargopt_dev.db"


class FakeBot:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, *, chat_id, text, **kwargs):
        self.messages.append((chat_id, text, kwargs))


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)


def reset_db() -> None:
    if DATA_DIR == PROJECT_ROOT / "data":
        raise RuntimeError("smoke must not delete PROJECT_ROOT/data")
    if DATA_DIR.exists():
        shutil.rmtree(DATA_DIR)
    DATA_DIR.mkdir(exist_ok=True)


def main() -> None:
    os.environ["BOT_TOKEN"] = "123456:TESTTOKEN"
    os.environ["DATABASE_URL"] = DATABASE_URL
    os.environ["ENVIRONMENT"] = "web-request-api-smoke"
    os.environ["LOG_LEVEL"] = "INFO"

    reset_db()

    import asyncio
    import app.models  # noqa: F401
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.db.base import Base

    async def create_test_schema() -> None:
        engine = create_async_engine(DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(create_test_schema())

    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.api.web_requests import get_api_bot

    fake_bot = FakeBot()

    async def override_bot():
        yield fake_bot

    app.dependency_overrides[get_api_bot] = override_bot

    payload = {
        "source_locale": "ru",
        "customer_name": "Web Client",
        "customer_email": "client@example.test",
        "preferred_contact": "whatsapp",
        "client_phone": "+351900000000",
        "client_whatsapp": "+351900000000",
        "utm_source": "landing",
        "utm_campaign": "lisbon_launch",
        "landing_version": "v1",
        "requested_date": "2026-07-01T10:00:00+00:00",
        "addresses": [
            {"kind": "pickup", "raw_text": "Lisboa", "floor": 2, "has_elevator": True},
            {"kind": "dropoff", "raw_text": "Porto", "floor": 0, "has_elevator": False},
        ],
        "items": [{"description": "10 boxes and washing machine", "quantity": 10}],
        "needs_assembly": False,
        "needs_packing": False,
        "needs_tail_lift": False,
        "needs_crane": False,
        "needs_mobile_lift": False,
        "required_loaders": 2,
        "estimated_payload_kg": 500,
        "estimated_volume_m3": 3.0,
        "comment": "Submitted from web form",
    }

    with TestClient(app) as client:
        health = client.get("/health")
        if health.status_code != 200:
            raise SystemExit(f"health failed: {health.status_code} {health.text}")

        response = client.post("/api/v1/requests", json=payload)

    if response.status_code != 200:
        raise SystemExit(f"unexpected response: {response.status_code} {response.text}")

    body = response.json()
    if not body.get("job_id"):
        raise SystemExit("job_id missing")
    if body.get("status") != "manual_review_required":
        raise SystemExit(f"unexpected status: {body.get('status')}")
    if not body.get("tracking_token"):
        raise SystemExit("tracking_token missing")
    tracking_prefix = {
        "en": "/en/track",
        "ru": "/ru/track",
    }.get(payload.get("source_locale"), "/track")
    expected_tracking_url = f"{tracking_prefix}/{body['tracking_token']}"
    if body.get("tracking_url") != expected_tracking_url:
        raise SystemExit(
            f"unexpected tracking_url: "
            f"{body.get('tracking_url')} != {expected_tracking_url}"
        )
    if body.get("offers_count") != 0:
        raise SystemExit(f"unexpected offers_count: {body.get('offers_count')}")
    if body.get("sent_count") != 0:
        raise SystemExit(f"unexpected sent_count: {body.get('sent_count')}")
    if not fake_bot.messages:
        raise SystemExit("manual review admin notification was not sent")

    shutil.rmtree(DATA_DIR)
    print("WEB_REQUEST_API_SMOKE_OK")


if __name__ == "__main__":
    main()
