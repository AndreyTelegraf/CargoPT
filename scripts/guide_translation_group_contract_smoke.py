from copy import deepcopy
from pathlib import Path

from scripts.corpus_release_audit import Audit


ALTERNATES = {
    "en": "/en/guides/how-to-leave-portugal/",
    "ru": (
        "/ru/guides/"
        "kak-pravilno-uehat-iz-portugalii/"
    ),
    "pt-BR": (
        "/pt-br/guias/"
        "como-sair-de-portugal/"
    ),
}


def load_validator():
    try:
        from scripts.corpus_release_audit import (  # noqa: PLC0415
            validate_translation_groups,
        )
    except ImportError as error:
        raise AssertionError(
            "MISSING_TRANSLATION_GROUP_VALIDATOR"
        ) from error

    return validate_translation_groups


def article(
    *,
    article_id: str,
    locale: str,
    path: str,
    group: str = "leave-portugal",
    alternates: dict[str, str] | None = None,
) -> tuple[Path, dict]:
    return (
        Path(f"{article_id}.json"),
        {
            "id": article_id,
            "locale": locale,
            "path": path,
            "translation_group": group,
            "alternates": deepcopy(
                ALTERNATES if alternates is None else alternates
            ),
        },
    )


def valid_group() -> list[tuple[Path, dict]]:
    return [
        article(
            article_id="leave-portugal-en",
            locale="en",
            path=ALTERNATES["en"],
        ),
        article(
            article_id="leave-portugal-ru",
            locale="ru",
            path=ALTERNATES["ru"],
        ),
        article(
            article_id="leave-portugal-pt-br",
            locale="pt-BR",
            path=ALTERNATES["pt-BR"],
        ),
    ]


def error_codes(audit: Audit) -> list[str]:
    return [
        finding.code
        for finding in audit.findings
        if finding.severity == "error"
    ]


def require_success(
    validate_translation_groups,
    articles: list[tuple[Path, dict]],
) -> None:
    audit = Audit()
    validate_translation_groups(audit, articles)

    codes = error_codes(audit)

    if codes:
        raise AssertionError(
            f"unexpected translation group errors: {codes}"
        )


def require_failure(
    validate_translation_groups,
    articles: list[tuple[Path, dict]],
    expected_code: str,
) -> None:
    audit = Audit()
    validate_translation_groups(audit, articles)

    codes = error_codes(audit)

    if expected_code not in codes:
        raise AssertionError(
            f"expected {expected_code!r}, got {codes!r}"
        )


def main() -> None:
    validate_translation_groups = load_validator()

    require_success(
        validate_translation_groups,
        [],
    )

    require_success(
        validate_translation_groups,
        valid_group(),
    )

    missing_target = valid_group()[:-1]
    require_failure(
        validate_translation_groups,
        missing_target,
        "MISSING_TRANSLATION_TARGET",
    )

    mismatched_alternates = valid_group()
    mismatched_alternates[1][1]["alternates"] = {
        "en": ALTERNATES["en"],
        "ru": ALTERNATES["ru"],
    }
    require_failure(
        validate_translation_groups,
        mismatched_alternates,
        "TRANSLATION_ALTERNATES_MISMATCH",
    )

    duplicate_locale = valid_group()
    duplicate_locale.append(
        article(
            article_id="leave-portugal-en-copy",
            locale="en",
            path="/en/guides/leaving-portugal-copy/",
            alternates={
                **ALTERNATES,
                "en": "/en/guides/leaving-portugal-copy/",
            },
        )
    )
    require_failure(
        validate_translation_groups,
        duplicate_locale,
        "DUPLICATE_TRANSLATION_LOCALE",
    )

    wrong_group = valid_group()
    wrong_group[2][1]["translation_group"] = "other-group"
    require_failure(
        validate_translation_groups,
        wrong_group,
        "TRANSLATION_TARGET_GROUP_MISMATCH",
    )

    duplicate_path_target = valid_group()
    duplicate_path_target.append(
        article(
            article_id="unrelated-en",
            locale="en",
            path=ALTERNATES["en"],
            group="unrelated",
            alternates={
                "en": ALTERNATES["en"],
                "ru": "/ru/guides/unrelated/",
            },
        )
    )
    require_failure(
        validate_translation_groups,
        duplicate_path_target,
        "AMBIGUOUS_TRANSLATION_TARGET",
    )

    print(
        "GUIDE_TRANSLATION_GROUP_CONTRACT_SMOKE_OK",
        2,
        5,
    )


if __name__ == "__main__":
    main()
