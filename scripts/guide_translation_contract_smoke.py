from copy import deepcopy

from scripts.guide_translation_contract import (
    validate_guide_translation_contract,
)


BASE_ARTICLE = {
    "id": "leave-portugal-en",
    "locale": "en",
    "path": "/en/guides/how-to-leave-portugal/",
    "translation_group": "leave-portugal",
    "alternates": {
        "en": "/en/guides/how-to-leave-portugal/",
        "ru": (
            "/ru/guides/"
            "kak-pravilno-uehat-iz-portugalii/"
        ),
        "pt-BR": (
            "/pt-br/guias/"
            "como-sair-de-portugal/"
        ),
    },
}


def require_success(article: dict) -> None:
    validate_guide_translation_contract(article)


def require_failure(
    article: dict,
    expected_message: str,
) -> None:
    try:
        validate_guide_translation_contract(article)
    except ValueError as error:
        if expected_message not in str(error):
            raise AssertionError(
                f"unexpected error: {error}"
            ) from error
    else:
        raise AssertionError(
            "expected ValueError containing "
            f"{expected_message!r}"
        )


def main() -> None:
    require_success(deepcopy(BASE_ARTICLE))

    standalone = {
        "id": "existing-pt-guide",
        "locale": "pt-PT",
        "path": "/guias/planeamento/checklist-mudanca/",
    }
    require_success(standalone)

    missing_alternates = deepcopy(BASE_ARTICLE)
    del missing_alternates["alternates"]
    require_failure(
        missing_alternates,
        "INCOMPLETE_TRANSLATION_METADATA",
    )

    missing_group = deepcopy(BASE_ARTICLE)
    del missing_group["translation_group"]
    require_failure(
        missing_group,
        "INCOMPLETE_TRANSLATION_METADATA",
    )

    empty_group = deepcopy(BASE_ARTICLE)
    empty_group["translation_group"] = "   "
    require_failure(
        empty_group,
        "INVALID_TRANSLATION_GROUP",
    )

    too_small = deepcopy(BASE_ARTICLE)
    too_small["alternates"] = {
        "en": "/en/guides/how-to-leave-portugal/",
    }
    require_failure(
        too_small,
        "INSUFFICIENT_TRANSLATION_ALTERNATES",
    )

    missing_self = deepcopy(BASE_ARTICLE)
    del missing_self["alternates"]["en"]
    require_failure(
        missing_self,
        "MISSING_SELF_ALTERNATE",
    )

    wrong_self = deepcopy(BASE_ARTICLE)
    wrong_self["alternates"]["en"] = (
        "/en/guides/different-path/"
    )
    require_failure(
        wrong_self,
        "SELF_ALTERNATE_PATH_MISMATCH",
    )

    unsupported_locale = deepcopy(BASE_ARTICLE)
    unsupported_locale["alternates"]["pt"] = (
        "/guias/planeamento/como-sair-de-portugal/"
    )
    require_failure(
        unsupported_locale,
        "UNSUPPORTED_GUIDE_LOCALE",
    )

    wrong_prefix = deepcopy(BASE_ARTICLE)
    wrong_prefix["alternates"]["ru"] = (
        "/en/guides/kak-pravilno-uehat-iz-portugalii/"
    )
    require_failure(
        wrong_prefix,
        "INVALID_GUIDE_PATH_PREFIX",
    )

    duplicate_paths = deepcopy(BASE_ARTICLE)
    duplicate_paths["alternates"]["ru"] = (
        "/en/guides/how-to-leave-portugal/"
    )
    require_failure(
        duplicate_paths,
        "DUPLICATE_ALTERNATE_PATH",
    )

    print(
        "GUIDE_TRANSLATION_CONTRACT_SMOKE_OK",
        2,
        9,
    )


if __name__ == "__main__":
    main()
