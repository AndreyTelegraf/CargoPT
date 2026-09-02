from datetime import UTC
from datetime import datetime

from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.web_request_schemas import AcquisitionEventPayload
from app.models.job import AcquisitionEventDaily


def _dimension(value: str | None, *, lowercase: bool = False) -> str:
    normalized = (value or "").strip()
    return normalized.lower() if lowercase else normalized


async def record_acquisition_event(
    session: AsyncSession,
    payload: AcquisitionEventPayload,
) -> None:
    now = datetime.now(UTC)
    values = {
        "event_date": now.date(),
        "event_type": payload.event_type,
        "source_locale": payload.source_locale,
        "utm_source": _dimension(payload.utm_source, lowercase=True),
        "utm_medium": _dimension(payload.utm_medium, lowercase=True),
        "utm_campaign": _dimension(payload.utm_campaign),
        "utm_content": _dimension(payload.utm_content),
        "referrer_host": _dimension(payload.referrer_host, lowercase=True),
        "landing_version": _dimension(payload.landing_version),
        "error_category": payload.error_category,
        "event_count": 1,
        "created_at": now,
        "updated_at": now,
    }
    dimensions = [
        "event_date",
        "event_type",
        "source_locale",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "referrer_host",
        "landing_version",
        "error_category",
    ]
    statement = insert(AcquisitionEventDaily).values(**values)
    statement = statement.on_conflict_do_update(
        index_elements=dimensions,
        set_={
            "event_count": AcquisitionEventDaily.event_count + 1,
            "updated_at": now,
        },
    )
    await session.execute(statement)
