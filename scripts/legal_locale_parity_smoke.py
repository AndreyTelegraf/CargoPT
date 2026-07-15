from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

GROUPS = {
    "privacy": {
        "pt": STATIC / "privacy/index.html",
        "en": STATIC / "en/privacy/index.html",
        "ru": STATIC / "ru/privacy/index.html",
        "x_default": (
            "https://cargopt.pt/privacy/"
        ),
    },
    "terms": {
        "pt": STATIC / "terms/index.html",
        "en": STATIC / "en/terms/index.html",
        "ru": STATIC / "ru/terms/index.html",
        "x_default": (
            "https://cargopt.pt/terms/"
        ),
    },
    "cookies": {
        "pt": STATIC / "cookies/index.html",
        "en": STATIC / "en/cookies/index.html",
        "ru": STATIC / "ru/cookies/index.html",
        "x_default": (
            "https://cargopt.pt/cookies/"
        ),
    },
}

EXPECTED = {
    "privacy": {
        "pt": (
            "https://cargopt.pt/privacy/",
            "Política de Privacidade — CargoPT",
            (
                "Como a CargoPT recolhe, utiliza, "
                "partilha e protege dados pessoais."
            ),
            "pt-PT",
            "https://cargopt.pt/#website",
            "/privacy/",
        ),
        "en": (
            "https://cargopt.pt/en/privacy/",
            "Privacy Policy — CargoPT",
            (
                "How CargoPT collects, uses, shares "
                "and protects personal data."
            ),
            "en",
            "https://cargopt.pt/en/#website",
            "/en/privacy/",
        ),
        "ru": (
            "https://cargopt.pt/ru/privacy/",
            (
                "Политика конфиденциальности — CargoPT"
            ),
            (
                "Как CargoPT собирает, использует, "
                "передаёт и защищает персональные данные."
            ),
            "ru",
            "https://cargopt.pt/ru/#website",
            "/ru/privacy/",
        ),
    },
    "terms": {
        "pt": (
            "https://cargopt.pt/terms/",
            "Termos e Condições — CargoPT",
            (
                "Termos aplicáveis à utilização do site "
                "e ao envio de pedidos através da CargoPT."
            ),
            "pt-PT",
            "https://cargopt.pt/#website",
            "/terms/",
        ),
        "en": (
            "https://cargopt.pt/en/terms/",
            "Terms and Conditions — CargoPT",
            (
                "Terms applying to the CargoPT site "
                "and request service."
            ),
            "en",
            "https://cargopt.pt/en/#website",
            "/en/terms/",
        ),
        "ru": (
            "https://cargopt.pt/ru/terms/",
            "Условия использования — CargoPT",
            (
                "Условия использования сайта CargoPT "
                "и отправки заявок на перевозку."
            ),
            "ru",
            "https://cargopt.pt/ru/#website",
            "/ru/terms/",
        ),
    },
    "cookies": {
        "pt": (
            "https://cargopt.pt/cookies/",
            "Política de Cookies — CargoPT",
            (
                "Informação sobre cookies e armazenamento "
                "local utilizado pela CargoPT."
            ),
            "pt-PT",
            "https://cargopt.pt/#website",
            "/cookies/",
        ),
        "en": (
            "https://cargopt.pt/en/cookies/",
            "Cookie Policy — CargoPT",
            (
                "Information about cookies and local "
                "storage used by CargoPT."
            ),
            "en",
            "https://cargopt.pt/en/#website",
            "/en/cookies/",
        ),
        "ru": (
            "https://cargopt.pt/ru/cookies/",
            "Политика cookies — CargoPT",
            (
                "Информация о cookies и локальном "
                "хранении данных на сайте CargoPT."
            ),
            "ru",
            "https://cargopt.pt/ru/#website",
            "/ru/cookies/",
        ),
    },
}

IMAGE = (
    "https://cargopt.pt/assets/brand/"
    "og-image-v8.jpg"
)


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags = Counter()
        self.tokens = []

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

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))


def parse_structure(path: Path):
    parser = StructureParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


for group, files in GROUPS.items():
    parsed = {
        locale: parse_structure(files[locale])
        for locale in ("pt", "en", "ru")
    }

    for locale in ("en", "ru"):
        assert (
            parsed[locale].tags
            == parsed["pt"].tags
        ), (group, locale, "tags")

        assert (
            parsed[locale].tokens
            == parsed["pt"].tokens
        ), (group, locale, "tokens")

    print(
        f"LEGAL_STRUCTURE_PARITY_OK={group}"
    )


for group, files in GROUPS.items():
    for locale in ("pt", "en", "ru"):
        path = files[locale]
        source = path.read_text(
            encoding="utf-8"
        )

        (
            canonical,
            title,
            description,
            language,
            website,
            current_path,
        ) = EXPECTED[group][locale]

        assert (
            f'<link rel="canonical" '
            f'href="{canonical}">'
        ) in source

        assert (
            '<link rel="alternate" '
            'hreflang="x-default" '
            f'href="{files["x_default"]}">'
        ) in source

        assert (
            f'<meta property="og:title" '
            f'content="{title}">'
        ) in source

        assert (
            '<meta property="og:description" '
            f'content="{description}">'
        ) in source

        assert (
            f'<meta property="og:url" '
            f'content="{canonical}">'
        ) in source

        assert (
            f'<meta property="og:image" '
            f'content="{IMAGE}">'
        ) in source

        assert (
            '<meta property="og:image:width" '
            'content="1200">'
        ) in source

        assert (
            '<meta property="og:image:height" '
            'content="630">'
        ) in source

        assert (
            '<meta name="twitter:card" '
            'content="summary_large_image">'
        ) in source

        assert (
            f'<meta name="twitter:title" '
            f'content="{title}">'
        ) in source

        assert (
            '<meta name="twitter:description" '
            f'content="{description}">'
        ) in source

        assert (
            f'<meta name="twitter:image" '
            f'content="{IMAGE}">'
        ) in source

        current = re.findall(
            r'<a href="([^"]+)" '
            r'aria-current="page">',
            source,
        )

        assert current == [current_path], (
            path,
            current,
        )

        scripts = re.findall(
            r'<script type="application/ld\+json">'
            r'(.*?)</script>',
            source,
            re.S,
        )

        assert len(scripts) == 1, (
            path,
            len(scripts),
        )

        data = json.loads(scripts[0])

        assert data["@type"] == "WebPage"
        assert data["@id"] == (
            canonical + "#webpage"
        )
        assert data["url"] == canonical
        assert data["name"] == title
        assert data["description"] == description
        assert data["inLanguage"] == language
        assert data["isPartOf"]["@id"] == website
        assert data["about"]["@id"] == (
            "https://cargopt.pt/#organization"
        )
        assert (
            data["primaryImageOfPage"]
            == IMAGE
        )

print("LEGAL_CANONICAL_AND_HREFLANG_OK")
print("LEGAL_OPEN_GRAPH_METADATA_OK")
print("LEGAL_TWITTER_METADATA_OK")
print("LEGAL_STRUCTURED_DATA_OK")
print("LEGAL_ACTIVE_LOCALE_LINKS_OK")
print("LEGAL_LOCALE_PARITY_SMOKE_OK")
