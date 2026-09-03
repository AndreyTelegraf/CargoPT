from datetime import UTC
from datetime import datetime
from datetime import timedelta


SHORT_LEAD_TIME_WARNING_HOURS = 72


_WARNING_COPY = {
    "pt": (
        "Faltam menos de três dias para o transporte. Por isso, o pedido não "
        "foi enviado automaticamente aos transportadores e ficou guardado para "
        "análise manual pela CargoPT. Para iniciar a procura automática, altere "
        "a data para pelo menos três dias a partir de agora."
    ),
    "en": (
        "There are fewer than three days before the transport. The request was "
        "therefore not sent automatically to carriers and has been saved for "
        "manual review by CargoPT. To start the automatic search, change the "
        "date to at least three days from now."
    ),
    "ru": (
        "До перевозки осталось меньше трёх суток. Поэтому заявка не была "
        "автоматически разослана перевозчикам и сохранена для ручной проверки "
        "CargoPT. Чтобы запустить автоматический поиск, измените дату на срок не ранее "
        "чем через трое суток."
    ),
}


def normalize_warning_locale(
    locale: str | None,
    *,
    default_locale: str = "pt",
) -> str:
    normalized = (locale or "").strip().lower().replace("_", "-")
    if normalized == "en" or normalized.startswith("en-"):
        return "en"
    if normalized == "ru" or normalized.startswith("ru-"):
        return "ru"
    if normalized == "pt" or normalized.startswith("pt-"):
        return "pt"
    return default_locale if default_locale in _WARNING_COPY else "pt"


def has_short_lead_time(
    requested_date: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    if requested_date is None:
        return False

    target = requested_date
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    else:
        target = target.astimezone(UTC)

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)

    lead_time = target - current
    return timedelta(0) <= lead_time < timedelta(
        hours=SHORT_LEAD_TIME_WARNING_HOURS
    )


def should_filter_short_lead_time(
    requested_date: datetime | None,
    *,
    now: datetime | None = None,
) -> bool:
    """Return whether automatic carrier distribution must be held."""
    if requested_date is None:
        return False

    target = requested_date
    if target.tzinfo is None:
        target = target.replace(tzinfo=UTC)
    else:
        target = target.astimezone(UTC)

    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)

    return target - current < timedelta(
        hours=SHORT_LEAD_TIME_WARNING_HOURS
    )


def short_lead_time_warning_text(
    locale: str | None,
    *,
    default_locale: str = "pt",
) -> str:
    normalized = normalize_warning_locale(
        locale,
        default_locale=default_locale,
    )
    return _WARNING_COPY[normalized]
