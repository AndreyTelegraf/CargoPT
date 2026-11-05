"""Enable only reliability events without changing third-party logging."""
import logging


def configure_reliability_logging():
    for name in (
        "app.services.telegram_dispatcher",
        "app.services.telegram_notifications",
        "app.scheduler.offer_expiry",
        "app.scheduler.assignment_timeout",
    ):
        logger = logging.getLogger(name)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
