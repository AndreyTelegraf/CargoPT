import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.domain.requested_date import RequestedDateInPastError
from app.domain.requested_date import is_requested_date_in_past
from app.domain.requested_date import validate_requested_date_not_in_past


def main() -> None:
    portugal = ZoneInfo("Europe/Lisbon")
    now = datetime(2026, 8, 1, 0, 30, tzinfo=portugal)

    assert is_requested_date_in_past(
        datetime(2026, 7, 31, 23, 59, tzinfo=portugal),
        now=now,
    )
    assert not is_requested_date_in_past(
        datetime(2026, 8, 1, 0, 0, tzinfo=portugal),
        now=now,
    )
    assert not is_requested_date_in_past(
        datetime(2026, 8, 2, 0, 0, tzinfo=portugal),
        now=now,
    )
    assert not is_requested_date_in_past(None, now=now)

    # 23:30 UTC is already the next calendar day in Portugal during DST.
    assert not is_requested_date_in_past(
        datetime(2026, 7, 31, 23, 30, tzinfo=UTC),
        now=now,
    )

    try:
        validate_requested_date_not_in_past(
            datetime(2026, 7, 31, 12, 0, tzinfo=UTC),
            now=now,
        )
    except RequestedDateInPastError:
        pass
    else:
        raise AssertionError("past requested date must be rejected")

    validate_requested_date_not_in_past(
        datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
        now=now,
    )

    print("REQUESTED_DATE_VALIDATION_SMOKE_OK")


if __name__ == "__main__":
    main()
