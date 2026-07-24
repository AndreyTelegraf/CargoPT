from urllib.parse import urljoin


def build_tracking_path(locale: str | None, token: str) -> str:
    normalized = (locale or "").strip().lower().replace("_", "-")
    prefix = {
        "en": "/en/track",
        "ru": "/ru/track",
    }.get(normalized, "/track")
    return f"{prefix}/{token}"


def build_tracking_url(
    locale: str | None,
    token: str,
    public_base_url: str,
) -> str:
    base = public_base_url.rstrip("/") + "/"
    return urljoin(base, build_tracking_path(locale, token).lstrip("/"))
