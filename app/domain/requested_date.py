from datetime import UTC
from datetime import datetime
from zoneinfo import ZoneInfo


PORTUGAL_TIMEZONE = ZoneInfo("Europe/Lisbon")


class RequestedDateInPastError(ValueError):
    pass


def _as_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone)


def is_requested_date_in_past(
    requested_date: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    if requested_date is None:
        return False

    current = now or datetime.now(PORTUGAL_TIMEZONE)
    current_local = _as_timezone(current, PORTUGAL_TIMEZONE)
    requested_local = _as_timezone(requested_date, PORTUGAL_TIMEZONE)
    return requested_local < current_local


def validate_requested_date_not_in_past(
    requested_date: datetime | None,
    *,
    now: datetime | None = None,
) -> None:
    if is_requested_date_in_past(requested_date, now=now):
        raise RequestedDateInPastError(
            "requested date must not be earlier than the current time in Portugal"
        )
