from scripts.guides_topics_registry_smoke import (
    expected_parent_for_topic,
)


CASES = (
    (
        {
            "path": "/guias/planeamento/checklist-mudanca/",
        },
        "/guias/",
    ),
    (
        {
            "path": "/mudancas-lisboa/",
        },
        "/guias/",
    ),
    (
        {
            "path": "/en/guides/how-to-leave-portugal/",
        },
        "/en/guides/",
    ),
    (
        {
            "path": (
                "/ru/guides/"
                "kak-pravilno-uehat-iz-portugalii/"
            ),
        },
        "/ru/guides/",
    ),
    (
        {
            "path": (
                "/pt-br/guias/"
                "como-sair-de-portugal/"
            ),
        },
        "/pt-br/guias/",
    ),
)


def main() -> None:
    for topic, expected in CASES:
        actual = expected_parent_for_topic(topic)

        assert actual == expected, (
            topic["path"],
            actual,
            expected,
        )

    print(
        "GUIDES_MULTILINGUAL_REGISTRY_SMOKE_OK",
        len(CASES),
    )


if __name__ == "__main__":
    main()
