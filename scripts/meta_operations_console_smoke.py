import asyncio
import base64
import os
from pathlib import Path
import tempfile


temp_dir = tempfile.TemporaryDirectory(prefix="cargopt-meta-ops-")
database_path = Path(temp_dir.name) / "meta_ops.db"
os.environ["BOT_TOKEN"] = "123456:smoke-test-token"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"
os.environ["META_OPERATIONS_ENABLED"] = "true"
os.environ["META_OPERATIONS_INBOUND_TOKEN"] = "inbound-smoke-secret"
os.environ["META_OPERATIONS_ADMIN_USERNAME"] = "operator"
os.environ["META_OPERATIONS_ADMIN_PASSWORD"] = "console-smoke-secret"
os.environ["META_OPERATIONS_TELEGRAM_CHAT_IDS"] = ""

from httpx import ASGITransport
from httpx import AsyncClient

from app.api.main import app as fastapi_app
from app.db.base import Base
from app.db.session import async_session_maker
from app.db.session import engine
import app.models  # noqa: F401
from app.repositories.meta_operations import MetaOperationsRepository
from app.services.meta_operations.classifier import classify_lead
from app.services.meta_operations.email_parser import parse_rfc822


async def main() -> None:
    bot_handler_source = Path(
        "app/bot/handlers/meta_operations.py"
    ).read_text(encoding="utf-8")
    enabled_guard = "if not settings.meta_operations_enabled:"
    access_guard = "if callback.from_user.id not in ("
    assert enabled_guard in bot_handler_source
    assert bot_handler_source.index(enabled_guard) < bot_handler_source.index(
        access_guard
    )

    target = classify_lead(
        "Olá, preciso de uma transportadora para levar um sofá de Lisboa para Porto. Recomendações?"
    )
    assert target.label == "target", target
    assert target.language == "pt", target
    offer = classify_lead(
        "Fazemos mudanças em Lisboa. Temos carrinha disponível. Contacte-nos para orçamento."
    )
    assert offer.label == "noise", offer

    parsed = parse_rfc822(
        b"From: Facebook <notification@facebookmail.com>\r\n"
        b"Subject: New group post\r\n"
        b"Message-ID: <smoke-1@example.com>\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Looking for a mover from Lisbon to Porto.\r\n"
        b"https://www.facebook.com/groups/123/posts/456/\r\n"
    )
    assert parsed.message_id == "<smoke-1@example.com>"
    assert parsed.urls == ("https://www.facebook.com/groups/123/posts/456/",)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        await MetaOperationsRepository(session).upsert_group(
            {
                "platform": "facebook",
                "external_id": "123",
                "name": "Portugal Transport Requests",
                "canonical_url": "https://www.facebook.com/groups/123/",
                "region": "Portugal",
                "category": "Community",
                "priority": 10,
                "review_status": "pilot",
                "activity": None,
                "ads_allowed": None,
                "rules_checked": "yes",
                "source_sheet": "smoke",
                "source_row": 1,
                "owner": None,
                "notes": None,
                "enabled": True,
            }
        )
        await session.commit()

    auth = "Basic " + base64.b64encode(
        b"operator:console-smoke-secret"
    ).decode("ascii")
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        inbound = {
            "message_id": "smoke-json-1",
            "sender": "notification@facebookmail.com",
            "subject": "New post in Portugal Transport Requests",
            "text": "Procuro uma transportadora para levar móveis de Lisboa para Porto. Alguém recomenda?",
            "source_url": "https://www.facebook.com/groups/123/posts/456/",
        }
        response = await client.post(
            "/api/v1/meta-operations/inbound/email",
            json=inbound,
            headers={"X-CargoPT-Inbound-Token": "inbound-smoke-secret"},
        )
        assert response.status_code == 200, response.text
        created = response.json()
        assert created["created"] is True, created
        assert created["classification"] == "target", created
        assert created["group_id"] is not None, created

        duplicate = await client.post(
            "/api/v1/meta-operations/inbound/email",
            json=inbound,
            headers={"X-CargoPT-Inbound-Token": "inbound-smoke-secret"},
        )
        assert duplicate.status_code == 200, duplicate.text
        assert duplicate.json()["created"] is False, duplicate.text

        unauthorized = await client.get("/api/v1/meta-operations/admin/summary")
        assert unauthorized.status_code == 401, unauthorized.text

        summary = await client.get(
            "/api/v1/meta-operations/admin/summary",
            headers={"Authorization": auth},
        )
        assert summary.status_code == 200, summary.text
        assert summary.json()["new"] == 1, summary.text
        assert summary.json()["groups_enabled"] == 1, summary.text

        events = await client.get(
            "/api/v1/meta-operations/admin/events",
            headers={"Authorization": auth},
        )
        assert events.status_code == 200, events.text
        assert len(events.json()) == 1, events.text

        handled = await client.patch(
            f"/api/v1/meta-operations/admin/events/{created['event_id']}/status",
            json={"status": "handled"},
            headers={"Authorization": auth},
        )
        assert handled.status_code == 200, handled.text
        assert handled.json()["status"] == "handled", handled.text

        console = await client.get(
            "/meta-operations",
            headers={"Authorization": auth},
        )
        assert console.status_code == 200, console.text
        assert "CargoPT · Meta Operations" in console.text

    await engine.dispose()
    temp_dir.cleanup()
    print("META_OPERATIONS_CONSOLE_SMOKE_OK")


if __name__ == "__main__":
    asyncio.run(main())
