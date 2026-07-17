from copy import deepcopy

from scripts.render_guide import render_guide
from scripts.render_guide_verbatim_smoke import ARTICLE, REGISTRY


def main() -> None:
    article = deepcopy(ARTICLE)
    article["sections"] = [
        {
            "id": "ordered-content",
            "heading": "Жильё и машина",
            "blocks": [
                {
                    "type": "paragraph",
                    "text": "Первый абзац.",
                },
                {
                    "type": "checklist",
                    "items": [
                        "Первый пункт.",
                        "Второй пункт.",
                    ],
                },
                {
                    "type": "paragraph",
                    "text": "Абзац после списка.",
                },
                {
                    "type": "subheading",
                    "text": "Отдельный случай",
                },
                {
                    "type": "paragraph",
                    "text": "Абзац после подзаголовка.",
                },
            ],
        }
    ]

    rendered = render_guide(article, deepcopy(REGISTRY))

    needles = [
        "<p>Первый абзац.</p>",
        "<li>Первый пункт.</li>",
        "<li>Второй пункт.</li>",
        "<p>Абзац после списка.</p>",
        "<h3>Отдельный случай</h3>",
        "<p>Абзац после подзаголовка.</p>",
    ]

    positions = []

    for needle in needles:
        assert needle in rendered, (
            "MISSING_ORDERED_BLOCK_CONTENT",
            needle,
        )
        positions.append(rendered.index(needle))

    assert positions == sorted(positions), (
        "ORDERED_BLOCK_SEQUENCE_CHANGED",
        positions,
    )

    print("RENDER_GUIDE_ORDERED_BLOCKS_SMOKE_OK")


if __name__ == "__main__":
    main()
