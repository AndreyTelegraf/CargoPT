import json
from pathlib import Path

from scripts.render_guide import render_guide


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTICLES_ROOT = PROJECT_ROOT / "content/guides/articles"
REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"

EXPECTED_HREFS = {
    "pt-PT": "/#request",
    "pt-BR": "/#request",
    "en": "/en/#request",
    "ru": "/ru/#request",
}


def main() -> None:
    registry = json.loads(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )
    checked = 0

    for article_path in sorted(ARTICLES_ROOT.glob("*.json")):
        article = json.loads(
            article_path.read_text(encoding="utf-8")
        )
        locale = article["locale"]
        expected_href = EXPECTED_HREFS[locale]
        rendered = render_guide(article, registry)
        header = rendered.split("</header>", 1)[0]
        expected = (
            '<a class="button button-small button-carrier" '
            f'href="{expected_href}">'
        )

        if header.count(expected) != 1:
            raise AssertionError(
                "LOCALE_HEADER_CTA_MISMATCH:"
                f"{article_path.name}:"
                f"locale={locale}:"
                f"expected_href={expected_href}"
            )

        if locale in {"en", "ru"}:
            if 'href="/#request"' in rendered:
                raise AssertionError(
                    "LOCALE_BODY_CTA_FELL_BACK_TO_PT:"
                    f"{article_path.name}:locale={locale}"
                )
            if rendered.count(f'href="{expected_href}"') < 2:
                raise AssertionError(
                    "LOCALE_BODY_CTA_MISSING:"
                    f"{article_path.name}:"
                    f"expected_href={expected_href}"
                )

        checked += 1

    print("RENDER_GUIDE_LOCALE_HEADER_CTA_SMOKE_OK")
    print("RENDER_GUIDE_LOCALE_BODY_CTA_SMOKE_OK")
    print(f"CHECKED_ARTICLES={checked}")


if __name__ == "__main__":
    main()
