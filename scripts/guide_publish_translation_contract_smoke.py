from copy import deepcopy

from scripts.guide_publish_preflight import (
    validate_article_registry_contract,
)


BASE_ARTICLE = {
    "id": "leave-portugal-en",
    "locale": "en",
    "cluster": "planning",
    "path": "/en/guides/how-to-leave-portugal/",
    "title": "How to leave Portugal",
    "primary_query": "how to leave Portugal",
    "intent": ["informational"],
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

BASE_TOPIC = {
    "id": "leave-portugal-en",
    "cluster": "planning",
    "path": "/en/guides/how-to-leave-portugal/",
    "title": "How to leave Portugal",
    "primary_query": "how to leave Portugal",
    "intent": ["informational"],
    "status": "draft",
}


def require_success(article: dict) -> None:
    validate_article_registry_contract(
        article,
        deepcopy(BASE_TOPIC),
    )


def require_failure(
    article: dict,
    expected_message: str,
) -> None:
    try:
        validate_article_registry_contract(
            article,
            deepcopy(BASE_TOPIC),
        )
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

    standalone = deepcopy(BASE_ARTICLE)
    standalone.pop("translation_group")
    standalone.pop("alternates")
    require_success(standalone)

    missing_alternates = deepcopy(BASE_ARTICLE)
    del missing_alternates["alternates"]
    require_failure(
        missing_alternates,
        "INCOMPLETE_TRANSLATION_METADATA",
    )

    wrong_self = deepcopy(BASE_ARTICLE)
    wrong_self["alternates"]["en"] = (
        "/en/guides/different-path/"
    )
    require_failure(
        wrong_self,
        "SELF_ALTERNATE_PATH_MISMATCH",
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
        "GUIDE_PUBLISH_TRANSLATION_CONTRACT_SMOKE_OK",
        2,
        4,
    )


if __name__ == "__main__":
    main()
