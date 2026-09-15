from datetime import UTC
from datetime import datetime
from datetime import timedelta


SHORT_LEAD_TIME_WARNING_HOURS = 72


_WARNING_COPY = {
    "pt": (
        "Faltam menos de 72 horas para o transporte. A CargoPT irá, ainda assim, "
        "iniciar a procura automática entre transportadores adequados. Por ser um "
        "pedido urgente, a disponibilidade e as propostas não são garantidas."
    ),
    "en": (
        "There are fewer than 72 hours before the transport. CargoPT will still "
        "start the automatic search among suitable carriers. Because the request "
        "is urgent, carrier availability and offers are not guaranteed."
    ),
    "ru": (
        "До перевозки осталось меньше 72 часов. CargoPT всё равно запустит "
        "автоматический поиск среди подходящих перевозчиков. Из-за срочности "
        "доступность перевозчиков и предложения не гарантируются."
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
