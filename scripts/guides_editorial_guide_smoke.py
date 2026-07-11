from pathlib import Path


def main() -> None:
    path = Path("content/guides/editorial-guide.md")

    assert path.is_file()

    text = path.read_text(encoding="utf-8")

    required_sections = [
        "# CargoPT Editorial Guide",
        "## 1. Editorial purpose",
        "## 3. Voice and tone",
        "## 4. Accuracy standard",
        "## 5. Search intent",
        "## 6. Standard article structure",
        "## 9. Price content",
        "## 10. City and local guides",
        "## 13. CargoPT positioning",
        "## 14. Conversion rules",
        "## 15. Internal linking",
        "## 16. Metadata",
        "## 17. Structured data",
        "## 19. Sources and citations",
        "## 20. AI and answer-engine readiness",
        "## 24. Pre-publication checklist",
        "## 25. First-guide implementation standard",
    ]

    for section in required_sections:
        assert section in text, section

    required_rules = [
        "Portuguese (Portugal)",
        "Content must never withhold the answer",
        "Never invent:",
        "The first substantive block must answer the query immediately.",
        "Do not publish price tables until their methodology and source date can be shown.",
        "Do not promise a specific number of proposals.",
        "Do not promise the lowest price.",
        "Do not link to planned pages",
        "The registry status is `published`.",
        "`Quanto custa uma mudança em Portugal?`",
        "it must not invent price ranges",
    ]

    for rule in required_rules:
        assert rule in text, rule

    forbidden = [
        "write like ",
        "in the style of ",
        "guaranteed lowest price",
    ]

    lowered = text.lower()

    for phrase in forbidden:
        assert phrase not in lowered, phrase

    assert len(text.splitlines()) >= 500
    assert text.endswith("\n")

    print(
        "GUIDES_EDITORIAL_GUIDE_SMOKE_OK",
        len(text.splitlines()),
        len(text.split()),
    )


if __name__ == "__main__":
    main()
