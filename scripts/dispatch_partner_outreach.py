import argparse
import asyncio
import fcntl
from pathlib import Path

from app.config import settings
from app.db.session import async_session_maker
from app.services.email.smtp_transport import SmtpEmailTransport
from app.services.partner_outreach.dispatcher import PartnerOutreachDispatcher


async def run(*, dry_run: bool) -> None:
    if not settings.partner_outreach_enabled:
        print("PARTNER_OUTREACH_DISABLED")
        return
    if not dry_run and not settings.partner_outreach_send_enabled:
        print("PARTNER_OUTREACH_SEND_DISABLED")
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
    dispatcher = PartnerOutreachDispatcher(
        session_maker=async_session_maker,
        transport=transport,
        enabled=settings.partner_outreach_send_enabled,
        from_name=settings.email_from_name,
        from_address=settings.email_from_address,
        reply_to=settings.email_reply_to,
        daily_limit=settings.partner_outreach_daily_limit,
        min_interval_minutes=settings.partner_outreach_min_interval_minutes,
        compliance_max_age_days=(
            settings.partner_outreach_compliance_max_age_days
        ),
        max_attempts=settings.email_max_attempts,
        retry_base_seconds=settings.email_retry_base_seconds,
    )
    processed, reason = await dispatcher.dispatch_due(dry_run=dry_run)
    print(f"PARTNER_OUTREACH_PROCESSED={processed}")
    print(f"PARTNER_OUTREACH_RESULT={reason}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    lock_path = Path("data/partner_outreach_dispatch.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a", encoding="utf-8") as lock_handle:
        try:
            fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("PARTNER_OUTREACH_ALREADY_RUNNING")
            return
        asyncio.run(run(dry_run=not args.send))


if __name__ == "__main__":
    main()
