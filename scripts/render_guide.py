import argparse
import html
import json
from pathlib import Path
from typing import Any

from scripts.atomic_write import atomic_write_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"
DEFAULT_STATIC_ROOT = PROJECT_ROOT / "app/static"


def escape_text(value: Any) -> str:
    return html.escape(str(value), quote=True)


def json_ld(data: dict[str, Any]) -> str:
    serialized = json.dumps(
        data,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.replace("</", "<\\/")


def public_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + "/" + path.strip("/") + "/"


def output_path_for_article(
    article: dict[str, Any],
    static_root: Path,
) -> Path:
    return static_root / article["path"].strip("/") / "index.html"


def render_paragraphs(paragraphs: list[str]) -> str:
    return "\n".join(
        f"        <p>{escape_text(paragraph)}</p>"
        for paragraph in paragraphs
    )


def render_items(items: list[dict[str, str]]) -> str:
    cards = "\n".join(
        (
            '          <article class="card guide-item-card">\n'
            f"            <h3>{escape_text(item['title'])}</h3>\n"
            f"            <p>{escape_text(item['text'])}</p>\n"
            "          </article>"
        )
        for item in items
    )

    return (
        '        <div class="cards three guide-item-grid">\n'
        f"{cards}\n"
        "        </div>"
    )


def render_checklist(items: list[str]) -> str:
    rows = "\n".join(
        f"          <li>{escape_text(item)}</li>"
        for item in items
    )

    return (
        '        <ul class="guide-checklist">\n'
        f"{rows}\n"
        "        </ul>"
    )


def render_section(section: dict[str, Any]) -> str:
    blocks: list[str] = []

    if section.get("paragraphs"):
        blocks.append(render_paragraphs(section["paragraphs"]))

    if section.get("items"):
        blocks.append(render_items(section["items"]))

    if section.get("checklist"):
        blocks.append(render_checklist(section["checklist"]))

    body = "\n\n".join(blocks)

    return (
        f'    <section id="{escape_text(section["id"])}" '
        'class="section guide-section">\n'
        '      <div class="guide-content">\n'
        '        <div class="section-heading">\n'
        f'          <h2>{escape_text(section["heading"])}</h2>\n'
        "        </div>\n"
        f"{body}\n"
        "      </div>\n"
        "    </section>"
    )


def render_cta(
    cta: dict[str, str],
    class_name: str,
) -> str:
    return (
        f'    <section class="section {class_name}">\n'
        f"      <h2>{escape_text(cta['heading'])}</h2>\n"
        f"      <p>{escape_text(cta['text'])}</p>\n"
        f'      <a class="button" href="{escape_text(cta["href"])}">'
        f"{escape_text(cta['label'])}</a>\n"
        "    </section>"
    )


def render_faq(
    faq_items: list[dict[str, str]],
    heading: str,
) -> str:
    details = "\n".join(
        (
            "        <details>\n"
            f"          <summary>{escape_text(item['question'])}</summary>\n"
            f"          <p>{escape_text(item['answer'])}</p>\n"
            "        </details>"
        )
        for item in faq_items
    )

    return (
        '    <section class="section guide-section">\n'
        '      <div class="guide-content">\n'
        '        <div class="section-heading">\n'
        '          <p class="eyebrow">Perguntas frequentes</p>\n'
        f"          <h2>{escape_text(heading)}</h2>\n"
        "        </div>\n"
        '        <div class="faq">\n'
        f"{details}\n"
        "        </div>\n"
        "      </div>\n"
        "    </section>"
    )


def render_related_links(
    links: list[dict[str, str]],
    heading: str,
) -> str:
    rendered_links = "\n".join(
        (
            f'          <a href="{escape_text(link["href"])}">'
            f"{escape_text(link['title'])}</a>"
        )
        for link in links
    )

    return (
        '    <section class="section guide-section">\n'
        '      <div class="guide-content">\n'
        '        <div class="section-heading">\n'
        '          <p class="eyebrow">Continuar</p>\n'
        f"          <h2>{escape_text(heading)}</h2>\n"
        "        </div>\n"
        '        <div class="chips guide-related-links">\n'
        f"{rendered_links}\n"
        "        </div>\n"
        "      </div>\n"
        "    </section>"
    )


def build_structured_data(
    article: dict[str, Any],
    registry: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    url = public_url(
        registry["base_url"],
        article["path"],
    )
    image_url = (
        registry["base_url"].rstrip("/")
        + "/assets/brand/og-image-v1.png"
    )

    article_schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["meta_description"],
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
        "author": {
            "@type": "Organization",
            "name": article["review_owner"],
            "url": registry["base_url"].rstrip("/") + "/",
        },
        "publisher": {
            "@type": "Organization",
            "name": "CargoPT",
            "url": registry["base_url"].rstrip("/") + "/",
        },
        "datePublished": article["date_published"],
        "dateModified": article["date_modified"],
        "image": image_url,
        "articleSection": article["article_section"],
        "inLanguage": article["locale"],
        "url": url,
    }

    breadcrumb_schema = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "CargoPT",
                "item": registry["base_url"].rstrip("/") + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": "Guias",
                "item": public_url(
                    registry["base_url"],
                    registry["guides_hub"],
                ),
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": article["title"],
                "item": url,
            },
        ],
    }

    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item["question"],
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item["answer"],
                },
            }
            for item in article["faq"]
        ],
    }

    return article_schema, breadcrumb_schema, faq_schema


def render_guide(
    article: dict[str, Any],
    registry: dict[str, Any],
) -> str:
    url = public_url(
        registry["base_url"],
        article["path"],
    )
    image_url = (
        registry["base_url"].rstrip("/")
        + "/assets/brand/og-image-v1.png"
    )

    article_schema, breadcrumb_schema, faq_schema = (
        build_structured_data(article, registry)
    )

    section_html = "\n\n".join(
        render_section(section)
        for section in article["sections"]
    )

    key_points = "\n".join(
        f"          <li>{escape_text(item)}</li>"
        for item in article["key_points"]
    )

    return f'''<!doctype html>
<html lang="{escape_text(article["locale"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape_text(article["meta_title"])}</title>
  <meta name="description" content="{escape_text(article["meta_description"])}">
  <link rel="canonical" href="{escape_text(url)}">
  <link rel="alternate" hreflang="pt-PT" href="{escape_text(url)}">
  <link rel="alternate" hreflang="x-default" href="{escape_text(url)}">
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="CargoPT">
  <meta property="og:title" content="{escape_text(article["meta_title"])}">
  <meta property="og:description" content="{escape_text(article["meta_description"])}">
  <meta property="og:url" content="{escape_text(url)}">
  <meta property="og:image" content="{escape_text(image_url)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{escape_text(image_url)}">
  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" type="image/svg+xml" href="/assets/brand/cargopt-icon.svg">
  <link rel="apple-touch-icon" href="/assets/brand/apple-touch-icon.png">
  <link rel="manifest" href="/site.webmanifest">
  <meta name="theme-color" content="#075BFF">
  <script type="application/ld+json">{json_ld(article_schema)}</script>
  <script type="application/ld+json">{json_ld(breadcrumb_schema)}</script>
  <script type="application/ld+json">{json_ld(faq_schema)}</script>
  <link rel="stylesheet" href="/assets/css/design-system.css?v=tokens-v1">
  <link rel="stylesheet" href="/assets/css/components.css?v=components-v1">
  <link rel="stylesheet" href="/assets/css/landing.css?v=design-unified-v1">
  <link rel="stylesheet" href="/assets/css/guides.css?v=guides-v1">
</head>
<body data-locale="pt" class="guide-page">
  <header class="site-header">
    <a class="logo" href="/" aria-label="CargoPT"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></a>
    <nav class="header-actions" aria-label="Navigation">
      <span class="locale-switcher">
        <button class="locale-current" type="button" aria-label="Choose language">PT</button>
        <span class="locale-menu">
          <a href="/guias/" aria-current="page">PT</a>
          <a href="/en/">EN</a>
          <a href="/ru/">RU</a>
        </span>
      </span>
      <a class="button button-small button-carrier" href="/#request">Receber propostas</a>
    </nav>
  </header>

  <main id="top">
    <nav class="section guide-breadcrumb" aria-label="Breadcrumb">
      <a href="/">CargoPT</a>
      <span aria-hidden="true">→</span>
      <a href="/guias/">Guias</a>
      <span aria-hidden="true">→</span>
      <span aria-current="page">{escape_text(article["title"])}</span>
    </nav>

    <header class="section guide-hero">
      <div class="guide-content">
        <p class="eyebrow">{escape_text(article["eyebrow"])}</p>
        <h1>{escape_text(article["title"])}</h1>
        <p class="hero-text">{escape_text(article["hero_description"])}</p>
        <p class="guide-meta">
          Publicado em <time datetime="{escape_text(article["date_published"])}">{escape_text(article["date_published"])}</time>
          · Revisto por {escape_text(article["review_owner"])}
        </p>
      </div>
    </header>

    <section class="section guide-section guide-direct-answer">
      <div class="guide-content">
        <div class="section-heading">
          <p class="eyebrow">Resposta direta</p>
          <h2>{escape_text(article["direct_answer_heading"])}</h2>
        </div>
        <p>{escape_text(article["direct_answer"])}</p>
      </div>
    </section>

    <section class="section guide-section">
      <div class="guide-content">
        <div class="section-heading">
          <p class="eyebrow">Pontos principais</p>
          <h2>{escape_text(article["key_points_heading"])}</h2>
        </div>
        <ul class="guide-key-points">
{key_points}
        </ul>
      </div>
    </section>

{section_html}

{render_cta(article["mid_cta"], "final-cta guide-mid-cta")}

{render_faq(
    article["faq"],
    article["faq_heading"],
)}

{render_related_links(
    article["related_links"],
    article["related_links_heading"],
)}

{render_cta(article["final_cta"], "final-cta guide-final-cta")}
  </main>

  <footer class="site-footer">
    <strong class="footer-logo"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></strong>
    <span>Guias e pedidos para mudanças e transporte em Portugal.</span>
    <a href="mailto:hello@cargopt.pt">hello@cargopt.pt</a>
  </footer>
</body>
</html>
'''


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render one CargoPT guide article to static HTML.",
    )
    parser.add_argument(
        "article",
        type=Path,
        help="Path to the structured guide article JSON file.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Path to the guides topic registry.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Explicit output path. Defaults to the public article path.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Render and validate without writing a file.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    article = load_json(args.article)
    registry = load_json(args.registry)
    rendered = render_guide(article, registry)

    assert rendered.startswith("<!doctype html>\n")
    assert rendered.endswith("</html>\n")

    output_path = args.output or output_path_for_article(
        article,
        DEFAULT_STATIC_ROOT,
    )

    if args.check:
        print(
            "GUIDE_RENDER_CHECK_OK",
            article["id"],
            len(rendered),
            output_path,
        )
        return

    if output_path.exists() and not args.force:
        raise FileExistsError(
            f"Output already exists: {output_path}. "
            "Use --force to replace it."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output_path, rendered)

    print(
        "GUIDE_RENDERED",
        article["id"],
        output_path,
        len(rendered),
    )


if __name__ == "__main__":
    main()
