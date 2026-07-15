from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

FILES = {
    "pt": STATIC / "transportadores/index.html",
    "en": STATIC / "en/carriers/index.html",
    "ru": STATIC / "ru/carriers/index.html",
}


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens = []
        self.tags = Counter()
        self.sections = []
        self.json_ld = []
        self.script_type = None
        self.script_parts = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)

        classes = " ".join(
            sorted(data.get("class", "").split())
        )

        self.tags[tag] += 1

        self.tokens.append(
            (
                "start",
                tag,
                classes,
                bool(data.get("id")),
                bool(data.get("href")),
                data.get("type"),
            )
        )

        if tag == "section":
            self.sections.append(classes)

        if tag == "script":
            self.script_type = data.get("type")
            self.script_parts = []

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))

        if tag == "script":
            if self.script_type == "application/ld+json":
                raw = "".join(self.script_parts).strip()

                if raw:
                    self.json_ld.append(raw)

            self.script_type = None
            self.script_parts = []

    def handle_data(self, data):
        if self.script_type:
            self.script_parts.append(data)


def parse(path: Path) -> StructureParser:
    parser = StructureParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


parsed = {
    locale: parse(path)
    for locale, path in FILES.items()
}

pt = parsed["pt"]

for locale in ("en", "ru"):
    current = parsed[locale]

    assert current.tokens == pt.tokens, locale
    assert current.tags == pt.tags, locale
    assert current.sections == pt.sections, locale

print("CARRIER_TAG_AND_CLASS_STRUCTURE_PARITY_OK")


EXPECTED = {
    "pt": {
        "canonical": "https://cargopt.pt/transportadores/",
        "home": "/",
        "terms": "/terms/",
        "privacy": "/privacy/",
        "current": "/transportadores/",
        "title": "Para transportadores — CargoPT",
        "required": (
            "Agregador",
            "de mudanças",
            "Para entrar<br>no nosso sistema",
            "O que precisamos para começar",
        ),
    },
    "en": {
        "canonical": "https://cargopt.pt/en/carriers/",
        "home": "/en/",
        "terms": "/en/terms/",
        "privacy": "/en/privacy/",
        "current": "/en/carriers/",
        "title": "For carriers — CargoPT",
        "required": (
            "Moving",
            "service aggregator",
            "To join<br>our system",
            "What we need to get started",
            "Receive requests",
        ),
    },
    "ru": {
        "canonical": "https://cargopt.pt/ru/carriers/",
        "home": "/ru/",
        "terms": "/ru/terms/",
        "privacy": "/ru/privacy/",
        "current": "/ru/carriers/",
        "title": "Перевозчикам — CargoPT",
        "required": (
            "Агрегатор",
            "услуг переезда",
            "Чтобы войти<br>в нашу систему",
            "Что нужно для начала работы",
            "Получать заявки",
        ),
    },
}


for locale, path in FILES.items():
    source = path.read_text(encoding="utf-8")
    expected = EXPECTED[locale]

    assert f"<title>{expected['title']}</title>" in source

    assert (
        f'<link rel="canonical" '
        f'href="{expected["canonical"]}">'
    ) in source

    assert (
        f'<meta property="og:url" '
        f'content="{expected["canonical"]}">'
    ) in source

    assert (
        f'<a class="logo" href="{expected["home"]}"'
    ) in source

    assert f'href="{expected["terms"]}"' in source
    assert f'href="{expected["privacy"]}"' in source

    assert (
        source.count(
            'href="https://t.me/andreytelegraf"'
        ) == 3
    )

    assert (
        source.count(
            'mailto:carriers@cargopt.pt'
        ) == 1
    )

    assert source.count(
        'class="carrier-join-steps"'
    ) == 1

    assert source.count(
        '<li><span class="field-required"'
    ) == 5

    legal = re.search(
        r'<ol class="legal-list">(.*?)</ol>',
        source,
        re.S,
    )

    assert legal is not None
    assert legal.group(1).count("<li>") == 9

    current_links = re.findall(
        r'<a href="([^"]+)" aria-current="page">',
        source,
    )

    assert current_links == [expected["current"]]

    for required in expected["required"]:
        assert required in source, (path, required)

    assert len(parsed[locale].json_ld) == 1

    data = json.loads(parsed[locale].json_ld[0])

    assert data["@type"] == "WebPage"
    assert data["name"] == expected["title"]
    assert data["url"] == expected["canonical"]

print("CARRIER_METADATA_AND_LINKS_OK")
print("CARRIER_ACTIVE_LOCALE_LINKS_OK")
print("CARRIER_ONBOARDING_STEPS_OK")
print("CARRIER_TERMS_CONTRACT_OK")
print("CARRIER_LOCALIZED_CONTENT_OK")


en = FILES["en"].read_text(encoding="utf-8")
ru = FILES["ru"].read_text(encoding="utf-8")

assert '<h2 class="carrier-card-step-title">' not in en
assert '<h2 class="carrier-card-step-title">' not in ru

assert (
    "CargoPT sends moving and transport requests "
    "to available carriers."
) not in en

assert (
    "CargoPT отправляет заявки на переезды "
    "и перевозки доступным перевозчикам."
) not in ru

assert 'aria-label="Навигация"' in ru
assert 'aria-label="Выбрать язык"' in ru

print("STALE_CARRIER_COPY_REMOVED_OK")
print("CARRIER_LOCALE_PARITY_SMOKE_OK")
