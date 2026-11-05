import asyncio
import logging

from app.db.session import async_session_maker
from app.services.offer_expiry import process_expired_pending_offers

logger = logging.getLogger(__name__)


async def run_offer_expiry_loop(
    *,
    bot,
    interval_seconds: int = 60,
) -> None:
    while True:
        try:
            async with async_session_maker() as session:
                processed = await process_expired_pending_offers(
                    bot=bot,
                    session=session,
                )
                if processed:
                    await session.commit()
                    logger.info("offer_expiry_job processed %s offers", processed)
                else:
                    await session.rollback()
                logger.info("offer_expiry_job cycle_complete processed=%s", processed)
        except Exception:
            logger.exception("offer_expiry_job failed")

        await asyncio.sleep(interval_seconds)
