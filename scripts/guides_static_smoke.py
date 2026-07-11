from pathlib import Path

from fastapi.testclient import TestClient

from app.api.main import app


def main() -> None:
    page = Path("app/static/guias/index.html")
    sitemap = Path("app/static/sitemap.xml")

    assert page.is_file()
    assert sitemap.is_file()

    html = page.read_text(encoding="utf-8")
    sitemap_text = sitemap.read_text(encoding="utf-8")

    required_html = [
        '<html lang="pt-PT">',
        '<link rel="canonical" href="https://cargopt.pt/guias/">',
        '"@type":"CollectionPage"',
        '"@type":"BreadcrumbList"',
        "<h1>Respostas práticas para mudanças e transporte em Portugal</h1>",
        'href="/mudancas-lisboa/"',
        'href="/mudancas-porto/"',
        'href="/mudancas-braga/"',
        'href="/mudancas-coimbra/"',
        'href="/transporte-moveis-lisboa/"',
        'href="/#request"',
    ]

    for expected in required_html:
        assert expected in html, expected

    assert html.count("<h1>") == 1
    assert "https://cargopt.pt/guias/" in sitemap_text
    assert "\\n</urlset>" not in sitemap_text
    assert sitemap_text.endswith("</urlset>\n")

    with TestClient(app) as client:
        response = client.get("/guias/")
        assert response.status_code == 200, response.status_code
        assert "Guias CargoPT" in response.text
        assert "Mudanças nas principais cidades" in response.text

    print("GUIDES_STATIC_SMOKE_OK")


if __name__ == "__main__":
    main()
