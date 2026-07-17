from copy import deepcopy

from scripts.guide_publish_preflight import (
    validate_article_registry_contract,
)


BASE_ARTICLE = {
    "id": "test-guide",
    "locale": "pt-PT",
    "cluster": "planning",
    "path": "/guias/planeamento/test-guide/",
    "title": "Test guide",
    "primary_query": "test guide",
    "intent": ["informational"],
}

BASE_TOPIC = {
    "id": "test-guide",
    "cluster": "planning",
    "path": "/guias/planeamento/test-guide/",
    "title": "Test guide",
    "primary_query": "test guide",
    "intent": ["informational"],
    "status": "draft",
}


def matching_case(
    *,
    locale: str,
    path: str,
) -> tuple[dict, dict]:
    article = deepcopy(BASE_ARTICLE)
    topic = deepcopy(BASE_TOPIC)

    article["locale"] = locale
    article["path"] = path
    topic["path"] = path

    return article, topic


def require_success(
    *,
    locale: str,
    path: str,
) -> None:
    article, topic = matching_case(
        locale=locale,
        path=path,
    )

    validate_article_registry_contract(
        article,
        topic,
    )


def require_failure(
    *,
    locale: str,
    path: str,
    expected_message: str,
) -> None:
    article, topic = matching_case(
        locale=locale,
        path=path,
    )

    try:
        validate_article_registry_contract(
            article,
            topic,
        )
    except ValueError as error:
        if expected_message not in str(error):
            raise AssertionError(
                f"unexpected error: {error}"
            ) from error
    else:
        raise AssertionError(
            "expected ValueError containing "
            f"{expected_message!r}: "
            f"locale={locale!r} path={path!r}"
        )


def main() -> None:
    valid_cases = (
        (
            "pt-PT",
            "/guias/planeamento/test-guide/",
        ),
        (
            "en",
            "/en/guides/test-guide/",
        ),
        (
            "ru",
            "/ru/guides/test-guide/",
        ),
        (
            "pt-BR",
            "/pt-br/guias/test-guide/",
        ),
    )

    for locale, path in valid_cases:
        require_success(
            locale=locale,
            path=path,
        )

    require_failure(
        locale="en",
        path="/guias/planeamento/test-guide/",
        expected_message="INVALID_GUIDE_PATH_PREFIX",
    )

    require_failure(
        locale="pt",
        path="/guias/planeamento/test-guide/",
        expected_message="UNSUPPORTED_GUIDE_LOCALE",
    )

    require_failure(
        locale="ru",
        path="/ru/guides/test-guide",
        expected_message="INVALID_GUIDE_PATH_SUFFIX",
    )

    print(
        "GUIDE_PUBLISH_LOCALE_CONTRACT_SMOKE_OK",
        len(valid_cases),
        3,
    )


if __name__ == "__main__":
    main()
