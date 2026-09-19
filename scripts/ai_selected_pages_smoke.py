import argparse
import html
import json
import re
import urllib.request
from pathlib import Path
from xml.etree import ElementTree


EXPECTED_DATE = "2026-09-05"
UPDATED_DATE = "2026-09-19"
UPDATED_PAGES = {
    "index.html",
    "en/index.html",
    "ru/index.html",
    "guias/objetos/como-transportar-frigorifico/index.html",
    "transporte-eletrodomesticos-lisboa/index.html",
}
UPDATED_SOURCES = {"como-transportar-frigorifico.json"}
PAGES = {
    "index.html": ("/", "Redação CargoPT"),
    "en/index.html": ("/en/", "CargoPT Editorial Team"),
    "ru/index.html": ("/ru/", "Редакция CargoPT"),
    "guias/objetos/como-transportar-frigorifico/index.html": (
        "/guias/objetos/como-transportar-frigorifico/",
        "Redação CargoPT",
    ),
    "en/guides/how-to-transport-a-refrigerator/index.html": (
        "/en/guides/how-to-transport-a-refrigerator/",
        "CargoPT Editorial Team",
    ),
    "ru/guides/kak-perevezti-holodilnik/index.html": (
        "/ru/guides/kak-perevezti-holodilnik/",
        "Редакция CargoPT",
    ),
    "guias/precos/quanto-custa-mudanca-porto/index.html": (
        "/guias/precos/quanto-custa-mudanca-porto/",
        "Redação CargoPT",
    ),
    "en/guides/moving-cost-porto/index.html": (
        "/en/guides/moving-cost-porto/",
        "CargoPT Editorial Team",
    ),
    "ru/guides/stoimost-pereezda-portu/index.html": (
        "/ru/guides/stoimost-pereezda-portu/",
        "Редакция CargoPT",
    ),
    "transporte-eletrodomesticos-lisboa/index.html": (
        "/transporte-eletrodomesticos-lisboa/",
        "Redação CargoPT",
    ),
}
SOURCES = {
    "como-transportar-frigorifico.json": "Redação CargoPT",
    "how-to-transport-a-refrigerator-en.json": "CargoPT Editorial Team",
    "kak-perevezti-holodilnik-ru.json": "Редакция CargoPT",
    "quanto-custa-mudanca-porto.json": "Redação CargoPT",
    "moving-cost-porto-en.json": "CargoPT Editorial Team",
    "stoimost-pereezda-portu-ru.json": "Редакция CargoPT",
}
REQUIRED_LINKS = {
    "index.html": {
        "/guias/precos/quanto-custa-mudanca-porto/",
        "/guias/objetos/como-transportar-frigorifico/",
        "/transporte-eletrodomesticos-lisboa/",
    },
    "en/index.html": {
        "/en/guides/moving-cost-porto/",
        "/en/guides/how-to-transport-a-refrigerator/",
    },
    "ru/index.html": {
        "/ru/guides/stoimost-pereezda-portu/",
        "/ru/guides/kak-perevezti-holodilnik/",
    },
    "transporte-eletrodomesticos-lisboa/index.html": {
        "/guias/objetos/como-transportar-frigorifico/",
        "/guias/objetos/como-transportar-maquina-lavar/",
        "/guias/embalamento/como-embalar-eletrodomesticos/",
    },
}
OLD_PROMISES = (
    "Receba várias propostas com",
    "Receive several offers from",
    "Получите несколько предложений",
)


def plain_text(fragment: str) -> str:
    return " ".join(
        html.unescape(re.sub(r"<[^>]+>", "", fragment)).split()
    )


def structured_data(page: str) -> list[dict]:
    blocks = re.findall(
        r'<script\s+type="application/ld\+json">(.*?)</script>',
        page,
        flags=re.DOTALL,
    )
    assert blocks, "page has no JSON-LD"
    return [json.loads(block) for block in blocks]


def check_faq_parity(page: str, data: list[dict], label: str) -> None:
    faq = next((item for item in data if item.get("@type") == "FAQPage"), None)
    assert faq, f"{label}: FAQPage missing"
    visible = [plain_text(value) for value in re.findall(
        r"<summary>(.*?)</summary>", page, flags=re.DOTALL
    )]
    encoded = [item["name"] for item in faq["mainEntity"]]
    assert visible == encoded, f"{label}: visible FAQ differs from JSON-LD"


def check_static(project_root: Path) -> None:
    static_root = project_root / "app/static"
    source_root = project_root / "content/guides/articles"

    for filename, reviewer in SOURCES.items():
        payload = json.loads((source_root / filename).read_text(encoding="utf-8"))
        expected_date = UPDATED_DATE if filename in UPDATED_SOURCES else EXPECTED_DATE
        assert payload["date_modified"] == expected_date, filename
        assert payload["review_owner"] == reviewer, filename

    for relative, (public_path, reviewer) in PAGES.items():
        page = (static_root / relative).read_text(encoding="utf-8")
        assert reviewer in page, relative
        expected_date = UPDATED_DATE if relative in UPDATED_PAGES else EXPECTED_DATE
        assert expected_date in page, relative
        assert "77" in page, relative
        assert not any(phrase in page for phrase in OLD_PROMISES), relative
        data = structured_data(page)
        check_faq_parity(page, data, relative)
        for required_link in REQUIRED_LINKS.get(relative, set()):
            assert f'href="{required_link}"' in page, (relative, required_link)

        canonical_url = "https://cargopt.pt" + public_path
        assert canonical_url in page, relative

    root = ElementTree.parse(static_root / "sitemap.xml").getroot()
    namespace = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    dates = {
        item.findtext("s:loc", namespaces=namespace): item.findtext(
            "s:lastmod", namespaces=namespace
        )
        for item in root.findall("s:url", namespace)
    }
    for relative, (public_path, _) in PAGES.items():
        url = "https://cargopt.pt" + public_path
        expected_date = UPDATED_DATE if relative in UPDATED_PAGES else EXPECTED_DATE
        assert dates.get(url) == expected_date, (url, dates.get(url))


def check_public(base_url: str) -> None:
    for relative, (public_path, reviewer) in PAGES.items():
        request = urllib.request.Request(
            base_url.rstrip("/") + public_path + "?ai_selected_pages_smoke=1",
            headers={"Cache-Control": "no-cache", "User-Agent": "CargoPT verification"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200, public_path
            assert reviewer in body, public_path
            expected_date = UPDATED_DATE if relative in UPDATED_PAGES else EXPECTED_DATE
            assert expected_date in body, public_path
            assert "77" in body, public_path
            check_faq_parity(body, structured_data(body), public_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--public-base-url")
    args = parser.parse_args()
    check_static(args.project_root)
    if args.public_base_url:
        check_public(args.public_base_url)
    print("AI_SELECTED_PAGES_SMOKE_OK")


if __name__ == "__main__":
    main()
