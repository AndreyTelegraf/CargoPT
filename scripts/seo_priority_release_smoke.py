import json
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

NEW_GROUPS = [
    ["/mudancas-pequenas-lisboa/", "/en/small-moves-lisbon/", "/ru/nebolshoy-pereezd-lissabon/"],
    ["/transporte-urgente-portugal/", "/en/urgent-transport-portugal/", "/ru/srochnaya-perevozka-portugaliya/"],
    ["/servico-embalamento-desmontagem-montagem/", "/en/packing-disassembly-assembly/", "/ru/upakovka-razborka-sborka/"],
]

THIN_PAGES = [
    "/mudancas-escritorio-lisboa/",
    "/transportadora-porto/",
    "/transporte-cama-lisboa/",
]

P1_GUIDES = [
    "/transporte-sofa-lisboa/",
    "/transporte-frigorifico-lisboa/",
    "/guias/objetos/como-transportar-frigorifico/",
    "/guias/objetos/preparar-frigorifico-transporte/",
    "/guias/objetos/como-transportar-maquina-lavar/",
    "/guias/objetos/como-transportar-sofa/",
    "/guias/embalamento/como-embalar-louca/",
    "/guias/embalamento/como-embalar-televisao/",
]


class AuditParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.h1 = 0
        self.canonical = []
        self.alternates = {}
        self.schemas = []
        self._script = None

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "link" and data.get("rel") == "canonical":
            self.canonical.append(data.get("href"))
        if tag == "link" and data.get("rel") == "alternate" and data.get("hreflang"):
            self.alternates[data["hreflang"]] = data.get("href")
        if tag == "script" and data.get("type") == "application/ld+json":
            self._script = []

    def handle_data(self, data):
        if self._script is not None:
            self._script.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._script is not None:
            payload = "".join(self._script).strip()
            if payload:
                self.schemas.append(json.loads(payload))
            self._script = None


def file_for(path: str) -> Path:
    return STATIC / path.strip("/") / "index.html"


def audit_page(path: str, *, min_words: int = 250, require_limit: bool = True) -> AuditParser:
    filename = file_for(path)
    assert filename.is_file(), filename
    text = filename.read_text(encoding="utf-8")
    parser = AuditParser()
    parser.feed(text)
    assert parser.h1 == 1, (path, parser.h1)
    assert parser.canonical == [f"https://cargopt.pt{path}"], (path, parser.canonical)
    assert len(text.split()) >= min_words, (path, len(text.split()))
    if require_limit:
        lower = text.lower()
        assert ("não" in lower and "garant" in lower) or "not guaranteed" in lower or "does not guarantee" in lower or "не гарант" in lower, path
    return parser


def main() -> None:
    for group in NEW_GROUPS:
        expected = {f"https://cargopt.pt{path}" for path in group}
        for path in group:
            parser = audit_page(path, min_words=450)
            alternates = {url for lang, url in parser.alternates.items() if lang != "x-default"}
            assert alternates == expected, (path, alternates, expected)
            assert any(schema.get("@type") == "FAQPage" for schema in parser.schemas), path

    for path in THIN_PAGES:
        parser = audit_page(path, min_words=450)
        assert any(schema.get("@type") == "FAQPage" for schema in parser.schemas), path

    for path in P1_GUIDES:
        parser = audit_page(path, min_words=500, require_limit=False)
        assert "2026-09-19" in file_for(path).read_text(encoding="utf-8"), path

    appliance = file_for("/transporte-eletrodomesticos-lisboa/").read_text(encoding="utf-8")
    assert "dateModified\":\"2026-09-19" in appliance
    assert "77 pedidos" in appliance

    for path in ("/transportadores/", "/en/carriers/", "/ru/carriers/"):
        text = file_for(path).read_text(encoding="utf-8")
        assert "22" in text and "34" in text and "2026-09-19" in text, path

    price = file_for("/guias/precos/quanto-custa-uma-mudanca/").read_text(encoding="utf-8")
    assert "Como transformar os fatores de preço" in price
    route = file_for("/mudancas-lisboa-porto/").read_text(encoding="utf-8")
    assert "nos dois sentidos" in route
    assert "sentido Porto–Lisboa" in route

    sitemap = ElementTree.parse(STATIC / "sitemap.xml").getroot()
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = [node.text for node in sitemap.findall("s:url/s:loc", ns)]
    assert len(urls) == 211, len(urls)
    assert len(urls) == len(set(urls))
    assert "https://cargopt.pt/mudancas-porto-lisboa/" not in urls
    assert "https://cargopt.pt/guias/precos/fatores-preco-mudanca/" not in urls
    for group in NEW_GROUPS:
        for path in group:
            assert f"https://cargopt.pt{path}" in urls, path

    nginx = (ROOT / "deploy/nginx/cargopt_seo_redirects.conf").read_text(encoding="utf-8")
    assert nginx.count("return 301") == 4
    assert "mudancas-lisboa-porto" in nginx
    assert "quanto-custa-uma-mudanca" in nginx

    for path in ("/", "/en/", "/ru/"):
        text = file_for(path).read_text(encoding="utf-8")
        for linked in NEW_GROUPS:
            local = next(item for item in linked if item.startswith(path) or path == "/" and not item.startswith(("/en/", "/ru/")))
            assert f'href="{local}"' in text, (path, local)

    print("SEO_PRIORITY_RELEASE_SMOKE_OK", len(urls))


if __name__ == "__main__":
    main()
