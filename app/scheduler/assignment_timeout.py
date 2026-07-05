import asyncio
import logging

from app.db.session import async_session_maker
from app.services.assignment_timeout import process_stale_assignment_confirmations

logger = logging.getLogger(__name__)


async def run_assignment_timeout_loop(
    *,
    bot,
    interval_seconds: int = 3600,
) -> None:
    while True:
        try:
            async with async_session_maker() as session:
                processed = await process_stale_assignment_confirmations(
                    bot=bot,
                    session=session,
                )
                if processed:
                    await session.commit()
                    logger.info("assignment_timeout_job processed %s jobs", processed)
                else:
                    await session.rollback()
        except Exception:
            logger.exception("assignment_timeout_job failed")

        await asyncio.sleep(interval_seconds)
