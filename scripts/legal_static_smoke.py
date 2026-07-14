from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app/static"

legal_pages = [
    "privacy/index.html", "terms/index.html", "cookies/index.html",
    "en/privacy/index.html", "en/terms/index.html", "en/cookies/index.html",
    "ru/privacy/index.html", "ru/terms/index.html", "ru/cookies/index.html",
]

for path in sorted(STATIC.rglob("*.html")):
    text = path.read_text(encoding="utf-8")
    if '<footer class="site-footer">' not in text:
        continue
    assert text.count('<footer class="site-footer">') == 1, path
    assert text.count('class="footer-links"') == 1, path

for relative in legal_pages:
    text = (STATIC / relative).read_text(encoding="utf-8")
    assert "legal-content" in text
    assert "hello@cargopt.pt" in text

for relative in ("index.html", "en/index.html", "ru/index.html"):
    text = (STATIC / relative).read_text(encoding="utf-8")
    form = re.search(r'<form id="requestForm".*?</form>', text, re.S).group(0)
    assert form.count('class="privacy-notice"') == 1
    assert 'type="checkbox"' not in form

for relative in ("transportadores/index.html", "en/carriers/index.html", "ru/carriers/index.html"):
    text = (STATIC / relative).read_text(encoding="utf-8")
    assert text.count('class="section carrier-terms"') == 1

sitemap = (STATIC / "sitemap.xml").read_text(encoding="utf-8")
for relative in legal_pages:
    assert "https://cargopt.pt/" + relative.removesuffix("index.html") in sitemap

assert "/* CargoPT legal surface v1 */" in (STATIC / "assets/css/landing.css").read_text(encoding="utf-8")
assert 'class="footer-links"' in (ROOT / "scripts/render_guide.py").read_text(encoding="utf-8")
print("LEGAL_STATIC_SMOKE_OK")


# LEGAL_VISUAL_REFINEMENT_SMOKE_V1
footer_pattern = re.compile(
    r'<footer class="site-footer">.*?</footer>',
    re.I | re.S,
)

service_taglines = (
    "Serviço de pedidos para mudanças e transporte em Portugal.",
    "Request service for moving and transport in Portugal.",
    "Сервис заявок на переезды и перевозки по Португалии.",
    "Сервис заявок на перевозки и переезды в Португалии.",
    "Guias e pedidos para mudanças e transporte em Portugal.",
)

for path in sorted(STATIC.rglob("*.html")):
    text = path.read_text(encoding="utf-8")

    if 'class="footer-links"' not in text:
        continue

    footer = footer_pattern.search(text).group(0)

    for tagline in service_taglines:
        assert tagline not in footer, path

    relative = str(path.relative_to(STATIC))

    if not relative.startswith(("en/", "ru/")):
        assert (
            '<a href="/transportadores/">'
            'Para transportadores</a>'
        ) in footer, path

for relative in (
    "privacy/index.html",
    "en/privacy/index.html",
    "ru/privacy/index.html",
):
    text = (STATIC / relative).read_text(encoding="utf-8")
    prefix = text.split('<footer class="site-footer">', 1)[0]
    assert "privacy@cargopt.pt" in prefix
    assert "hello@cargopt.pt" not in prefix

for relative in (
    "terms/index.html",
    "en/terms/index.html",
    "ru/terms/index.html",
):
    text = (STATIC / relative).read_text(encoding="utf-8")
    prefix = text.split('<footer class="site-footer">', 1)[0]
    assert "support@cargopt.pt" in prefix
    assert "hello@cargopt.pt" not in prefix

for relative in (
    "transportadores/index.html",
    "en/carriers/index.html",
    "ru/carriers/index.html",
):
    text = (STATIC / relative).read_text(encoding="utf-8")
    assert text.count("carriers@cargopt.pt") == 2, relative

for relative in (
    "track/index.html",
    "en/track/index.html",
    "ru/track/index.html",
):
    text = (STATIC / relative).read_text(encoding="utf-8")

    body_start = text.lower().find("<body")

    assert body_start >= 0, relative

    body_end = text.find(">", body_start)

    assert body_end >= 0, relative

    body_tag = text[body_start:body_end + 1]

    classes = None

    for quote in ('"', "'"):
        marker = f"class={quote}"
        class_start = body_tag.find(marker)

        if class_start < 0:
            continue

        value_start = class_start + len(marker)
        value_end = body_tag.find(quote, value_start)

        assert value_end >= 0, relative

        classes = body_tag[value_start:value_end].split()
        break

    assert classes is not None, relative
    assert "track-page-shell" in classes, relative


css = (STATIC / "assets/css/landing.css").read_text(
    encoding="utf-8"
)

assert ".legal-hero > .eyebrow" in css
assert "color: #075BFF;" in css
assert ".site-footer a {" in css
assert "text-decoration: none;" in css
assert ".track-page-shell > .site-footer" in css

print("LEGAL_VISUAL_REFINEMENT_SMOKE_OK")
