import copy
import json
import re
from pathlib import Path

from scripts.render_guide import render_guide


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLE_PATH = (
    PROJECT_ROOT
    / "content/guides/articles/quanto-custa-uma-mudanca.json"
)
REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"

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

EXPECTED_LABELS = {
    "en": {
        "body_locale": "en",
        "guides": "Guides",
        "published": "Published on",
        "reviewed": "Reviewed by",
        "direct_answer": "Direct answer",
        "key_points": "Key points",
        "faq": "Frequently asked questions",
        "continue": "Continue",
        "request": "Get offers",
    },
    "ru": {
        "body_locale": "ru",
        "guides": "Статьи",
        "published": "Опубликовано",
        "reviewed": "Проверено",
        "direct_answer": "Короткий ответ",
        "key_points": "Главное",
        "faq": "Частые вопросы",
        "continue": "Читайте также",
        "request": "Получить предложения",
    },
    "pt-BR": {
        "body_locale": "pt-br",
        "guides": "Guias",
        "published": "Publicado em",
        "reviewed": "Revisado por",
        "direct_answer": "Resposta direta",
        "key_points": "Pontos principais",
        "faq": "Perguntas frequentes",
        "continue": "Continuar",
        "request": "Receber propostas",
    },
}


def load_fixture() -> tuple[dict, dict]:
    article = json.loads(
        ARTICLE_PATH.read_text(encoding="utf-8")
    )
    registry = json.loads(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )
    return article, registry


def build_article(
    source: dict,
    *,
    locale: str,
    path: str,
) -> dict:
    article = copy.deepcopy(source)

    article["id"] = f"leave-portugal-{locale.lower()}"
    article["locale"] = locale
    article["path"] = path
    article["translation_group"] = "leave-portugal"
    article["alternates"] = copy.deepcopy(ALTERNATES)

    return article


def extract_alternates(rendered: str) -> list[tuple[str, str]]:
    return re.findall(
        (
            r'<link rel="alternate" '
            r'hreflang="([^"]+)" '
            r'href="([^"]+)"'
        ),
        rendered,
    )


def inspect_render_contract(
    source: dict,
    registry: dict,
    *,
    locale: str,
    path: str,
) -> list[str]:
    article = build_article(
        source,
        locale=locale,
        path=path,
    )

    rendered = render_guide(article, registry)
    labels = EXPECTED_LABELS[locale]
    base_url = registry["base_url"].rstrip("/")
    failures: list[str] = []

    if f'<html lang="{locale}">' not in rendered:
        failures.append(f"HTML_LANG_MISMATCH:{locale}")

    expected_body = (
        f'<body data-locale="{labels["body_locale"]}" '
        'class="guide-page">'
    )

    if expected_body not in rendered:
        failures.append(f"BODY_LOCALE_MISMATCH:{locale}")

    expected_alternates = [
        (
            alternate_locale,
            base_url + alternate_path,
        )
        for alternate_locale, alternate_path
        in ALTERNATES.items()
    ]
    expected_alternates.append(
        (
            "x-default",
            base_url + ALTERNATES["en"],
        )
    )

    actual_alternates = extract_alternates(rendered)

    if actual_alternates != expected_alternates:
        failures.append(
            "HREFLANG_MISMATCH:"
            f"{locale}:"
            f"actual={actual_alternates}:"
            f"expected={expected_alternates}"
        )

    for key in (
        "guides",
        "published",
        "reviewed",
        "direct_answer",
        "key_points",
        "faq",
        "continue",
        "request",
    ):
        if labels[key] not in rendered:
            failures.append(
                f"LABEL_MISMATCH:{locale}:{key}:{labels[key]}"
            )

    forbidden_pt_labels = (
        "Revisto por",
        "Pontos principais",
        "Perguntas frequentes",
    )

    if locale != "pt-BR":
        for label in forbidden_pt_labels:
            if label in rendered:
                failures.append(
                    f"HARDCODED_PT_LABEL:{locale}:{label}"
                )

    print(
        "MULTILINGUAL_RENDER_CASE_INSPECTED",
        locale,
        len(rendered),
        len(actual_alternates),
        len(failures),
    )

    return failures


def main() -> None:
    source, registry = load_fixture()

    cases = (
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
            (
                "/pt-br/guias/"
                "como-sair-de-portugal/"
            ),
        ),
    )

    failures: list[str] = []

    for locale, path in cases:
        failures.extend(
            inspect_render_contract(
                source,
                registry,
                locale=locale,
                path=path,
            )
        )

    if failures:
        raise AssertionError(
            "MULTILINGUAL_RENDERER_CONTRACT_FAILURES:\\n"
            + "\\n".join(failures)
        )

    print(
        "GUIDES_MULTILINGUAL_RENDERER_SMOKE_OK",
        len(cases),
    )


if __name__ == "__main__":
    main()
