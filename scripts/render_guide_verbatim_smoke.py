from copy import deepcopy

from scripts.render_guide import render_guide


REGISTRY = {
    "base_url": "https://cargopt.pt/",
    "guides_hub": "/guias/",
}

ARTICLE = {
    "schema_version": 1,
    "id": "leave-portugal-ru",
    "locale": "ru",
    "cluster": "planning",
    "path": "/ru/guides/kak-pravilno-uehat-iz-portugalii/",
    "title": "Как правильно уехать из Португалии",
    "meta_title": "Как правильно уехать из Португалии — CargoPT",
    "meta_description": "Практический порядок закрытия дел перед отъездом.",
    "primary_query": "как уехать из Португалии",
    "intent": ["informational"],
    "article_section": "Переезд из Португалии",
    "eyebrow": "Переезд из Португалии",
    "hero_description": "ЭТОТ ТЕКСТ НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "date_published": "2026-07-17",
    "date_modified": "2026-07-17",
    "review_owner": "CargoPT",
    "direct_answer_heading": "ЭТОТ ЗАГОЛОВОК НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "key_points_heading": "ЭТОТ ЗАГОЛОВОК НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "faq_heading": "ЭТОТ ЗАГОЛОВОК НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "related_links_heading": "ЭТОТ ЗАГОЛОВОК НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "direct_answer": "Этот дополнительный редакционный текст не должен появиться.",
    "key_points": [
        "Этот дополнительный пункт не должен появиться."
    ],
    "content_mode": "verbatim",
    "sections": [
        {
            "id": "housing-car",
            "heading": "Жильё и машина",
            "paragraphs": [
                "Физически покинуть страну можно одним днём.",
                "Начинать нужно с квартиры:",
            ],
            "checklist": [
                "согласуйте дату осмотра;",
                "сфотографируйте квартиру.",
            ],
        },
        {
            "id": "final",
            "heading": "Финальный чек-лист:",
            "checklist": [
                "аренда расторгнута письменно;",
                "все подтверждения скачаны.",
            ],
            "paragraphs": [
                "Boa viagem!",
            ],
        },
    ],
    "mid_cta": {
        "heading": "НЕ ПОКАЗЫВАТЬ",
        "text": "НЕ ПОКАЗЫВАТЬ",
        "label": "НЕ ПОКАЗЫВАТЬ",
        "href": "/#request",
    },
    "faq": [
        {
            "question": "НЕ ПОКАЗЫВАТЬ?",
            "answer": "НЕ ПОКАЗЫВАТЬ",
        }
    ],
    "related_links": [
        {
            "title": "НЕ ПОКАЗЫВАТЬ",
            "href": "/guias/",
            "type": "guide",
        },
        {
            "title": "НЕ ПОКАЗЫВАТЬ",
            "href": "/#request",
            "type": "service",
        },
    ],
    "final_cta": {
        "heading": "НЕ ПОКАЗЫВАТЬ",
        "text": "НЕ ПОКАЗЫВАТЬ",
        "label": "НЕ ПОКАЗЫВАТЬ",
        "href": "/#request",
    },
}

FORBIDDEN = (
    "ЭТОТ ТЕКСТ НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "ЭТОТ ЗАГОЛОВОК НЕ ДОЛЖЕН ПОЯВИТЬСЯ",
    "Этот дополнительный редакционный текст",
    "Этот дополнительный пункт",
    "НЕ ПОКАЗЫВАТЬ",
    "guide-direct-answer",
    "guide-key-points",
    "guide-mid-cta",
    "guide-final-cta",
    'class="faq"',
    "guide-related-links",
)

REQUIRED = (
    "<h1>Как правильно уехать из Португалии</h1>",
    "<h2>Жильё и машина</h2>",
    "<p>Физически покинуть страну можно одним днём.</p>",
    "<p>Начинать нужно с квартиры:</p>",
    "<li>согласуйте дату осмотра;</li>",
    "<li>сфотографируйте квартиру.</li>",
    "<h2>Финальный чек-лист:</h2>",
    "<li>аренда расторгнута письменно;</li>",
    "<li>все подтверждения скачаны.</li>",
    "<p>Boa viagem!</p>",
)


def main() -> None:
    rendered = render_guide(
        deepcopy(ARTICLE),
        deepcopy(REGISTRY),
    )

    for needle in REQUIRED:
        assert needle in rendered, (
            "MISSING_VERBATIM_CONTENT",
            needle,
        )

    for needle in FORBIDDEN:
        assert needle not in rendered, (
            "NON_VERBATIM_CONTENT_RENDERED",
            needle,
        )

    assert rendered.count("<h1>") == 1
    assert rendered.count("<h2>") == 2

    print(
        "RENDER_GUIDE_VERBATIM_SMOKE_OK",
        len(rendered.encode("utf-8")),
    )


if __name__ == "__main__":
    main()
