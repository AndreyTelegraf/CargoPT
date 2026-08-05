import os


def _parse_telegram_user_ids(raw_value: str | None) -> frozenset[int]:
    if not raw_value:
        return frozenset()

    values: set[int] = set()

    for raw_item in raw_value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError(
                "Telegram user ID lists must contain only positive integers"
            )
        values.add(int(item))

    return frozenset(values)


ADMIN_TELEGRAM_USER_IDS = frozenset({336224597})

DISPATCHER_TELEGRAM_USER_IDS = _parse_telegram_user_ids(
    os.getenv("DISPATCHER_TELEGRAM_USER_IDS")
)

JOB_CONTROL_TELEGRAM_USER_IDS = (
    DISPATCHER_TELEGRAM_USER_IDS or ADMIN_TELEGRAM_USER_IDS
)

LEADS_REPORT_TELEGRAM_USER_IDS = _parse_telegram_user_ids(
    os.getenv("LEADS_REPORT_TELEGRAM_USER_IDS")
)

CARGOPT_OPERATOR_TELEGRAM_USER_IDS = (
    ADMIN_TELEGRAM_USER_IDS | DISPATCHER_TELEGRAM_USER_IDS
)

CARGOPT_LEADS_VIEWER_TELEGRAM_USER_IDS = (
    CARGOPT_OPERATOR_TELEGRAM_USER_IDS
    | LEADS_REPORT_TELEGRAM_USER_IDS
)
