from typing import Any

from scripts.guide_locale_contract import (
    validate_guide_locale_path,
)


def validate_guide_translation_contract(
    article: dict[str, Any],
) -> None:
    has_group = "translation_group" in article
    has_alternates = "alternates" in article

    if not has_group and not has_alternates:
        return

    if has_group != has_alternates:
        raise ValueError(
            "INCOMPLETE_TRANSLATION_METADATA:"
            f"{article.get('id', '<unknown>')}"
        )

    translation_group = article["translation_group"]
    alternates = article["alternates"]

    if (
        not isinstance(translation_group, str)
        or not translation_group.strip()
    ):
        raise ValueError(
            "INVALID_TRANSLATION_GROUP:"
            f"{article.get('id', '<unknown>')}"
        )

    if not isinstance(alternates, dict):
        raise ValueError(
            "INVALID_TRANSLATION_ALTERNATES:"
            f"{article.get('id', '<unknown>')}"
        )

    if len(alternates) < 2:
        raise ValueError(
            "INSUFFICIENT_TRANSLATION_ALTERNATES:"
            f"{article.get('id', '<unknown>')}"
        )

    locale = article["locale"]
    path = article["path"]

    if locale not in alternates:
        raise ValueError(
            "MISSING_SELF_ALTERNATE:"
            f"{article.get('id', '<unknown>')}:{locale}"
        )

    if alternates[locale] != path:
        raise ValueError(
            "SELF_ALTERNATE_PATH_MISMATCH:"
            f"{article.get('id', '<unknown>')}:"
            f"{locale}:{alternates[locale]}:{path}"
        )

    alternate_paths = list(alternates.values())

    if len(alternate_paths) != len(set(alternate_paths)):
        raise ValueError(
            "DUPLICATE_ALTERNATE_PATH:"
            f"{article.get('id', '<unknown>')}"
        )

    for alternate_locale, alternate_path in alternates.items():
        validate_guide_locale_path(
            locale=alternate_locale,
            path=alternate_path,
        )
