import asyncio
import logging

from app.db.session import async_session_maker
from app.services.job_lifecycle_notifications import (
    process_job_lifecycle_notifications,
)


logger = logging.getLogger(__name__)


async def run_job_lifecycle_loop(*, bot, interval_seconds: int = 300) -> None:
    while True:
        try:
            async with async_session_maker() as session:
                processed = await process_job_lifecycle_notifications(
                    bot=bot,
                    session=session,
                )
                if processed:
                    await session.commit()
                    logger.info(
                        "job_lifecycle_notifications processed %s jobs",
                        processed,
                    )
                else:
                    await session.rollback()
        except Exception:
            logger.exception("job_lifecycle_notifications failed")

        await asyncio.sleep(interval_seconds)
