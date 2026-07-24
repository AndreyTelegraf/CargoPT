import asyncio

from app.config import settings
from app.db.session import async_session_maker
from app.services.email.dispatcher import EmailDispatcher
from app.services.email.smtp_transport import SmtpEmailTransport


async def run() -> None:
    if not settings.email_enabled:
        print("EMAIL_DISPATCH_DISABLED")
        return

    transport = SmtpEmailTransport(
        hostname=settings.email_smtp_host,
        port=settings.email_smtp_port,
        username=settings.email_smtp_username,
        password=settings.email_smtp_password.get_secret_value(),
        start_tls=settings.email_smtp_starttls,
        use_tls=settings.email_smtp_use_tls,
        timeout_seconds=settings.email_timeout_seconds,
    )
    dispatcher = EmailDispatcher(
        session_maker=async_session_maker,
        transport=transport,
        public_base_url=settings.email_public_base_url,
        from_name=settings.email_from_name,
        from_address=settings.email_from_address,
        reply_to=settings.email_reply_to,
        max_attempts=settings.email_max_attempts,
        retry_base_seconds=settings.email_retry_base_seconds,
    )
    processed = await dispatcher.dispatch_due()
    print(f"EMAIL_DISPATCH_PROCESSED={processed}")


if __name__ == "__main__":
    asyncio.run(run())
