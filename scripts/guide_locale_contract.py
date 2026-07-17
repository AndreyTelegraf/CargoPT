import re
from typing import Final


GUIDE_PATH_PREFIX_BY_LOCALE: Final[dict[str, str]] = {
    "pt-PT": "/guias/",
    "en": "/en/guides/",
    "ru": "/ru/guides/",
    "pt-BR": "/pt-br/guias/",
}

PT_ROOT_LANDING_PATH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^/(?:mudancas|transportadora|transporte)"
    r"-[a-z0-9]+(?:-[a-z0-9]+)*/$"
)


def validate_guide_locale_path(
    *,
    locale: str,
    path: str,
) -> None:
    expected_prefix = GUIDE_PATH_PREFIX_BY_LOCALE.get(locale)

    if expected_prefix is None:
        raise ValueError(
            f"UNSUPPORTED_GUIDE_LOCALE:{locale}"
        )

    if not isinstance(path, str) or not path.endswith("/"):
        raise ValueError(
            f"INVALID_GUIDE_PATH_SUFFIX:{locale}:{path}"
        )

    if locale == "pt-PT":
        is_guide_path = path.startswith(expected_prefix)
        is_root_landing = bool(
            PT_ROOT_LANDING_PATH_PATTERN.fullmatch(path)
        )

        if is_guide_path or is_root_landing:
            return

        raise ValueError(
            "INVALID_GUIDE_PATH_PREFIX:"
            f"{locale}:{path}:"
            "expected=/guias/ or pt-root-landing"
        )

    if not path.startswith(expected_prefix):
        raise ValueError(
            "INVALID_GUIDE_PATH_PREFIX:"
            f"{locale}:{path}:expected={expected_prefix}"
        )
