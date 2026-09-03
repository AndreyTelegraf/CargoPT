from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

FILES = {
    "pt": STATIC / "track/index.html",
    "en": STATIC / "en/track/index.html",
    "ru": STATIC / "ru/track/index.html",
}

EXPECTED = {
    "pt": {
        "lang": "pt-PT",
        "locale": "pt",
        "title": (
            "CargoPT — estado do seu pedido"
        ),
        "description": (
            "Página privada para acompanhar o estado "
            "do seu pedido CargoPT."
        ),
        "home": "/",
        "current": "/track/",
        "copy": "Copiar track link",
        "sidebar": "Outros pedidos",
        "error": (
            "Não foi possível carregar este pedido"
        ),
        "footer": (
            "/transportadores/",
            "/privacy/",
            "/terms/",
            "/cookies/",
        ),
    },
    "en": {
        "lang": "en",
        "locale": "en",
        "title": "CargoPT — track your request",
        "description": (
            "Private page for tracking the status "
            "of your CargoPT request."
        ),
        "home": "/en/",
        "current": "/en/track/",
        "copy": "Copy tracking link",
        "sidebar": "Other requests",
        "error": "Unable to load this request",
        "footer": (
            "/en/carriers/",
            "/en/privacy/",
            "/en/terms/",
            "/en/cookies/",
        ),
    },
    "ru": {
        "lang": "ru",
        "locale": "ru",
        "title": (
            "CargoPT — статус вашей заявки"
        ),
        "description": (
            "Приватная страница для отслеживания "
            "статуса заявки CargoPT."
        ),
        "home": "/ru/",
        "current": "/ru/track/",
        "copy": "Скопировать ссылку",
        "sidebar": "Другие заявки",
        "error": "Не удалось загрузить заявку",
        "footer": (
            "/ru/carriers/",
            "/ru/privacy/",
            "/ru/terms/",
            "/ru/cookies/",
        ),
    },
}


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()

        self.tags = Counter()
        self.tokens = []
        self.ids = []

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
                "hidden" in data,
            )
        )

        if data.get("id"):
            self.ids.append(data["id"])

    def handle_endtag(self, tag):
        self.tokens.append(("end", tag))


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

    assert current.tags == pt.tags, (
        locale,
        current.tags,
        pt.tags,
    )

    assert current.tokens == pt.tokens, (
        locale,
        "tag/class structure differs",
    )

    assert current.ids == pt.ids, (
        locale,
        current.ids,
        pt.ids,
    )

print("TRACKING_TAG_CLASS_AND_ID_PARITY_OK")


REQUIRED_IDS = [
    "copyTrackingLink",
    "top",
    "trackingProgressHeader",
    "otherRequestsPanel",
    "otherRequestsToggle",
    "trackPedidosList",
    "trackingPanel",
    "trackingPanelBody",
    "errorCard",
]

assert pt.ids == REQUIRED_IDS, pt.ids


for locale, path in FILES.items():
    source = path.read_text(encoding="utf-8")
    expected = EXPECTED[locale]

    assert (
        f'<html lang="{expected["lang"]}">'
        in source
    )

    assert (
        f"<title>{expected['title']}</title>"
        in source
    )

    assert (
        '<meta name="robots" '
        'content="noindex,nofollow">'
        in source
    )

    assert (
        f'<meta name="description" '
        f'content="{expected["description"]}">'
        in source
    )

    assert (
        f'<body data-locale="{expected["locale"]}" '
        'class="tracking-page track-page-shell">'
        in source
    )

    assert (
        f'<a class="logo" href="{expected["home"]}"'
        in source
    )

    assert (
        source.count(
            'class="locale-switcher"'
        ) == 1
    )

    current_links = re.findall(
        r'<a href="([^"]+)" '
        r'aria-current="page">',
        source,
    )

    assert current_links == [
        expected["current"]
    ], (
        path,
        current_links,
    )

    assert (
        f">{expected['copy']}</button>"
        in source
    )

    assert (
        expected["sidebar"] in source
    )

    assert (
        expected["error"] in source
    )

    for href in expected["footer"]:
        assert f'href="{href}"' in source

    for asset in (
        (
            "/assets/css/components.css"
            "?v=carrier-profile-v1"
        ),
        (
            "/assets/css/track.css"
            "?v=short-lead-v1"
        ),
        (
            "/assets/css/progress-header.css"
            "?v=progress-cancelled-stage-v5"
        ),
        (
            "/assets/js/progress-header.js"
            "?v=progress-stage-v5"
        ),
        (
            "/assets/js/tracking-workspace.js"
            "?v=short-lead-filter-v1"
        ),
        (
            "/assets/js/track.js"
            "?v=short-lead-filter-v1"
        ),
    ):
        assert asset in source, (
            path,
            asset,
        )

    assert 'id="otherRequestsPanel"' in source
    assert 'id="otherRequestsToggle"' in source
    assert 'id="trackingProgressHeader"' in source
    assert 'track-new-request' not in source
    assert 'track-sidebar-eyebrow' not in source
    assert 'track-sidebar-intro' not in source

print("TRACKING_STATIC_COPY_AND_ASSETS_OK")
print("TRACKING_ACTIVE_LOCALE_LINKS_OK")
print("TRACKING_CURRENT_WORKSPACE_TEMPLATE_OK")


track_js = (
    STATIC / "assets/js/track.js"
).read_text(encoding="utf-8")

for required in (
    'PT: "/track"',
    'EN: "/en/track"',
    'RU: "/ru/track"',
    "function updateLocaleLinks()",
    "encodeURIComponent(token)",
    "updateLocaleLinks();",
):
    assert required in track_js, required

print("TRACK_TOKEN_LOCALE_LINK_CONTRACT_OK")


progress_js = (
    STATIC / "assets/js/progress-header.js"
).read_text(encoding="utf-8")

for required in (
    "const LOCALIZED_STEPS",
    'en: Object.freeze([',
    'ru: Object.freeze([',
    '{id: "received", label: "Received"}',
    '{id: "searching", label: "Searching"}',
    '{id: "offers", label: "Offers"}',
    '{id: "selection", label: "Selection"}',
    '{id: "confirmed", label: "Confirmed"}',
    '{id: "received", label: "Получено"}',
    '{id: "searching", label: "Поиск"}',
    '{id: "offers", label: "Предложения"}',
    '{id: "selection", label: "Выбор"}',
    '{id: "confirmed", label: "Подтверждено"}',
    "function getDefaultSteps()",
    "LOCALIZED_STEPS[getLocale()]",
    ": getDefaultSteps();",
):
    assert required in progress_js, required

for required in (
    'pt: "Cancelado"',
    'en: "Cancelled"',
    'ru: "Отменено"',
):
    assert required in progress_js, required

print("TRACKING_PROGRESS_STEPS_LOCALIZED_OK")
print("TRACKING_CANCELLED_LABELS_PRESERVED_OK")
print("TRACKING_LOCALE_PARITY_SMOKE_OK")
