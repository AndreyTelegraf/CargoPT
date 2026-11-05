import html


from app.bot.offer_locale import offer_text as t
from app.repositories.carrier import CarrierRepository
from app.repositories.job import JobRepository


def _safe(value) -> str:
    return html.escape(str(value), quote=False)


def _format_elevator(value, locale: str | None) -> str:
    if value is None:
        return t(locale, "not_provided")
    return t(locale, "yes") if value else t(locale, "no")


def _format_address(label_key: str, address, locale: str | None) -> str:
    raw_text = address.raw_text if address else None
    normalized_address = getattr(address, "normalized_address", None) if address else None
    map_url = address.map_url if address else None
    floor = address.floor if address else None
    has_elevator = address.has_elevator if address else None
    address_details = getattr(address, "address_details", None) if address else None

    value = _safe(normalized_address or raw_text or t(locale, "not_provided"))
    safe_label = _safe(t(locale, label_key))
    floor_value = floor if floor is not None else t(locale, "not_provided")
    details = (
        f"\n{t(locale, 'floor')}: {_safe(floor_value)}"
        f"\n{t(locale, 'elevator')}: {_format_elevator(has_elevator, locale)}"
    )
    if address_details:
        details += f"\n{t(locale, 'access')}: {_safe(address_details)}"
    elif raw_text and normalized_address and raw_text.casefold() != normalized_address.casefold():
        details += f"\n{t(locale, 'client_input')}: {_safe(raw_text)}"

    if map_url and map_url != raw_text:
        return f"<b>{safe_label}</b>\n{value}\n{t(locale, 'map')}: {_safe(map_url)}{details}"
    return f"<b>{safe_label}</b>\n{value}{details}"


def _format_requested_date(value, locale: str | None) -> str:
    if value is None:
        return f"<b>{t(locale, 'date_time')}</b>\n{t(locale, 'not_provided_plural')}"
    return f"<b>{t(locale, 'date_time')}</b>\n" + _safe(value.strftime("%d.%m.%Y %H:%M"))


def _format_value(value, suffix: str, locale: str | None) -> str:
    if value is None:
        return t(locale, "not_provided")
    return _safe(f"{value}{suffix}")


def _format_items(items, locale: str | None) -> str:
    descriptions = [_safe(item.description) for item in items if item.description]
    return "; ".join(descriptions) if descriptions else t(locale, "not_provided")


def build_offer_text(job, items, pickup, dropoff, locale: str | None = None) -> str:
    return (
        f"<b>{t(locale, 'new_request', job_id=job.id)}</b>\n\n"
        f"{_format_requested_date(job.requested_date, locale)}\n\n"
        f"{_format_address('pickup', pickup, locale)}\n\n"
        f"{_format_address('dropoff', dropoff, locale)}\n\n"
        f"<b>{t(locale, 'cargo')}</b>\n"
        f"{_format_items(items, locale)}\n\n"
        f"<b>{t(locale, 'parameters')}</b>\n"
        f"{t(locale, 'volume')}: {_format_value(job.estimated_volume_m3, ' м³', locale)}\n"
        f"{t(locale, 'loaders')}: {_format_value(job.required_loaders, '', locale)}\n\n"
        f"<b>{t(locale, 'comment')}</b>\n"
        f"{_safe(job.comment or t(locale, 'no_comment'))}\n\n"
        f"{t(locale, 'decision_prompt')}"
    )


async def send_job_offers_to_carriers(
    *,
    bot,
    job,
    offers,
    job_repository: JobRepository,
    carrier_repository: CarrierRepository,
) -> int:
    """Compatibility entry point: returns queued count, never calls Telegram.

    The caller owns commit. All distribution paths use the same offer business
    key as initial submission, including retries and dispatcher actions.
    """
    from app.services.telegram_notifications import notification_service_for

    queued = await notification_service_for(
        job_repository, carrier_repository
    ).enqueue_carrier_offers(job=job, offers=offers)
    return len(queued)
