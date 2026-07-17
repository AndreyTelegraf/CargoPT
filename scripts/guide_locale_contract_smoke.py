from scripts.guide_locale_contract import (
    validate_guide_locale_path,
)


def require_success(locale: str, path: str) -> None:
    validate_guide_locale_path(
        locale=locale,
        path=path,
    )


def require_failure(
    locale: str,
    path: str,
    expected_message: str,
) -> None:
    try:
        validate_guide_locale_path(
            locale=locale,
            path=path,
        )
    except ValueError as error:
        if expected_message not in str(error):
            raise AssertionError(
                f"unexpected error for {locale=} {path=}: {error}"
            ) from error
    else:
        raise AssertionError(
            f"expected failure for {locale=} {path=}"
        )


def main() -> None:
    valid_cases = (
        (
            "pt-PT",
            "/guias/planeamento/checklist-mudanca/",
        ),
        (
            "en",
            "/en/guides/how-to-leave-portugal/",
        ),
        (
            "ru",
            (
                "/ru/guides/"
                "kak-pravilno-uehat-iz-portugalii/"
            ),
        ),
        (
            "pt-BR",
            "/pt-br/guias/como-sair-de-portugal/",
        ),
    )

    for locale, path in valid_cases:
        require_success(locale, path)

    invalid_cases = (
        (
            "en",
            "/guias/planeamento/how-to-leave-portugal/",
            "INVALID_GUIDE_PATH_PREFIX",
        ),
        (
            "ru",
            "/en/guides/kak-pravilno-uehat-iz-portugalii/",
            "INVALID_GUIDE_PATH_PREFIX",
        ),
        (
            "pt-BR",
            "/guias/planeamento/como-sair-de-portugal/",
            "INVALID_GUIDE_PATH_PREFIX",
        ),
        (
            "pt-PT",
            "/pt-br/guias/como-sair-de-portugal/",
            "INVALID_GUIDE_PATH_PREFIX",
        ),
        (
            "pt",
            "/guias/planeamento/como-sair-de-portugal/",
            "UNSUPPORTED_GUIDE_LOCALE",
        ),
        (
            "en",
            "/en/guides/how-to-leave-portugal",
            "INVALID_GUIDE_PATH_SUFFIX",
        ),
    )

    for locale, path, expected_message in invalid_cases:
        require_failure(
            locale,
            path,
            expected_message,
        )

    print(
        "GUIDE_LOCALE_CONTRACT_SMOKE_OK",
        len(valid_cases),
        len(invalid_cases),
    )


if __name__ == "__main__":
    main()
