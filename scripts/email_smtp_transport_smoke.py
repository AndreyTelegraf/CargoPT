import asyncio

import aiosmtplib
from aiosmtplib.errors import SMTPAuthenticationError

from app.services.email.models import EmailMessage
from app.services.email.smtp_transport import SmtpEmailTransport
from app.services.email.transport import PermanentEmailTransportError


async def main() -> None:
    captured = {}
    original_send = aiosmtplib.send

    async def fake_send(message, **kwargs):
        captured["message"] = message
        captured["kwargs"] = kwargs
        return ({}, "queued-id-123")

    aiosmtplib.send = fake_send
    try:
        transport = SmtpEmailTransport(
            hostname="smtp.example.test",
            port=587,
            username="user",
            password="secret",
            start_tls=True,
            use_tls=False,
            timeout_seconds=15,
        )
        result = await transport.send(
            EmailMessage(
                to="client@example.test",
                subject="CargoPT — teste",
                text_body="plain",
                html_body="<p>html</p>",
                from_address="noreply@cargopt.pt",
                from_name="CargoPT",
                reply_to=None,
            )
        )
        assert result.provider_message_id == "queued-id-123"
        assert captured["kwargs"]["password"] == "secret"
        assert captured["message"].get_content_type() == "multipart/alternative"
        assert len(captured["message"].get_payload()) == 2

        async def reject_send(message, **kwargs):
            raise SMTPAuthenticationError(535, "rejected")

        aiosmtplib.send = reject_send
        try:
            await transport.send(
                EmailMessage(
                    to="client@example.test",
                    subject="test",
                    text_body="plain",
                    html_body="<p>html</p>",
                    from_address="noreply@cargopt.pt",
                    from_name="CargoPT",
                )
            )
        except PermanentEmailTransportError as exc:
            assert "secret" not in str(exc)
        else:
            raise AssertionError("SMTP authentication error was not mapped")
    finally:
        aiosmtplib.send = original_send

    print("EMAIL_SMTP_ADAPTER_OK")


asyncio.run(main())
