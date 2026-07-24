import argparse
import html
import json
from pathlib import Path
from typing import Any

from scripts.atomic_write import atomic_write_text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"
DEFAULT_STATIC_ROOT = PROJECT_ROOT / "app/static"

GUIDE_RENDER_LABELS = {
    "pt-PT": {
        "body_locale": "pt",
        "home_href": "/",
        "guides": "Guias",
        "guides_href": "/guias/",
        "published": "Publicado em",
        "reviewed": "Revisto por",
        "direct_answer": "Resposta direta",
        "key_points": "Pontos principais",
        "faq": "Perguntas frequentes",
        "continue": "Continuar",
        "request": "Receber propostas",
        "footer_aria": "Informação legal",
        "footer_carriers": "Para transportadores",
        "footer_carriers_href": "/transportadores/",
        "footer_privacy": "Privacidade",
        "footer_privacy_href": "/privacy/",
        "footer_terms": "Termos",
        "footer_terms_href": "/terms/",
        "footer_cookies": "Cookies",
        "footer_cookies_href": "/cookies/",
        "footer_contact": "Contacto",
    },
    "en": {
        "body_locale": "en",
        "home_href": "/en/",
        "guides": "Guides",
        "guides_href": "/en/guides/",
        "published": "Published on",
        "reviewed": "Reviewed by",
        "direct_answer": "Direct answer",
        "key_points": "Key points",
        "faq": "Frequently asked questions",
        "continue": "Continue",
        "request": "Get offers",
        "footer_aria": "Legal information",
        "footer_carriers": "Carriers",
        "footer_carriers_href": "/en/carriers/",
        "footer_privacy": "Privacy",
        "footer_privacy_href": "/en/privacy/",
        "footer_terms": "Terms",
        "footer_terms_href": "/en/terms/",
        "footer_cookies": "Cookies",
        "footer_cookies_href": "/en/cookies/",
        "footer_contact": "Contact",
    },
    "ru": {
        "body_locale": "ru",
        "home_href": "/ru/",
        "guides": "Статьи",
        "guides_href": "/ru/guides/",
        "published": "Опубликовано",
        "reviewed": "Проверено",
        "direct_answer": "Короткий ответ",
        "key_points": "Главное",
        "faq": "Частые вопросы",
        "continue": "Читайте также",
        "request": "Получить предложения",
        "footer_aria": "Юридическая информация",
        "footer_carriers": "Перевозчикам",
        "footer_carriers_href": "/ru/carriers/",
        "footer_privacy": "Конфиденциальность",
        "footer_privacy_href": "/ru/privacy/",
        "footer_terms": "Условия",
        "footer_terms_href": "/ru/terms/",
        "footer_cookies": "Cookies",
        "footer_cookies_href": "/ru/cookies/",
        "footer_contact": "Контакты",
    },
    "pt-BR": {
        "body_locale": "pt-br",
        "home_href": "/pt-br/",
        "guides": "Guias",
        "guides_href": "/pt-br/guias/",
        "published": "Publicado em",
        "reviewed": "Revisado por",
        "direct_answer": "Resposta direta",
        "key_points": "Pontos principais",
        "faq": "Perguntas frequentes",
        "continue": "Continuar",
        "request": "Receber propostas",
        "footer_aria": "Informações legais",
        "footer_carriers": "Para transportadoras",
        "footer_carriers_href": "/transportadores/",
        "footer_privacy": "Privacidade",
        "footer_privacy_href": "/privacy/",
        "footer_terms": "Termos",
        "footer_terms_href": "/terms/",
        "footer_cookies": "Cookies",
        "footer_cookies_href": "/cookies/",
        "footer_contact": "Contato",
    },
}


def guide_render_labels(locale: str) -> dict[str, str]:
    try:
        return GUIDE_RENDER_LABELS[locale]
    except KeyError as error:
        raise ValueError(
            f"UNSUPPORTED_GUIDE_RENDER_LOCALE:{locale}"
        ) from error


def render_hreflang_links(
    article: dict[str, Any],
    base_url: str,
    current_url: str,
) -> str:
    alternates = article.get("alternates")

    if not isinstance(alternates, dict):
        return (
            '  <link rel="alternate" '
            'hreflang="pt-PT" '
            f'href="{escape_text(current_url)}">\n'
            '  <link rel="alternate" '
            'hreflang="x-default" '
            f'href="{escape_text(current_url)}">'
        )

    rendered = []

    for locale, alternate_path in alternates.items():
        alternate_url = public_url(base_url, alternate_path)
        rendered.append(
            '  <link rel="alternate" '
            f'hreflang="{escape_text(locale)}" '
            f'href="{escape_text(alternate_url)}">'
        )

    default_path = (
        alternates.get("en")
        or alternates.get(article["locale"])
    )
    default_url = public_url(base_url, default_path)

    rendered.append(
        '  <link rel="alternate" '
        'hreflang="x-default" '
        f'href="{escape_text(default_url)}">'
    )

    return "\n".join(rendered)


LOCALE_SWITCHER_LABELS = {
    "pt-PT": "PT",
    "pt-BR": "PT",
    "en": "EN",
    "ru": "RU",
}


def render_locale_switcher(article: dict[str, Any]) -> str:
    current_locale = article["locale"]
    current_label = LOCALE_SWITCHER_LABELS[current_locale]
    alternates = article.get("alternates")

    if not isinstance(alternates, dict):
        return (
            '      <span class="locale-switcher">\n'
            '        <button class="locale-current" type="button" '
            'aria-label="Choose language">'
            f'{escape_text(current_label)}</button>\n'
            '        <span class="locale-menu">\n'
            f'          <a href="{escape_text(article["path"])}" '
            'aria-current="page">'
            f'{escape_text(current_label)}</a>\n'
            '        </span>\n'
            '      </span>'
        )

    links = []

    for locale, href in alternates.items():
        label = LOCALE_SWITCHER_LABELS[locale]
        current_attribute = (
            ' aria-current="page"'
            if locale == current_locale
            else ""
        )

        links.append(
            f'          <a href="{escape_text(href)}"'
            f'{current_attribute}>'
            f'{escape_text(label)}</a>'
        )

    return (
        '      <span class="locale-switcher">\n'
        '        <button class="locale-current" type="button" '
        'aria-label="Choose language">'
        f'{escape_text(current_label)}</button>\n'
        '        <span class="locale-menu">\n'
        + "\n".join(links)
        + '\n        </span>\n'
        '      </span>'
    )


def render_article_meta(
    article: dict[str, Any],
    labels: dict[str, str],
    *,
    indent: str,
) -> str:
    return (
        f'{indent}<p class="guide-meta">\n'
        f'{indent}  {escape_text(labels["published"])} '
        f'<time datetime="{escape_text(article["date_published"])}">'
        f'{escape_text(article["date_published"])}</time>\n'
        f'{indent}  · {escape_text(labels["reviewed"])} '
        f'{escape_text(article["review_owner"])}\n'
        f'{indent}</p>'
    )


def render_article_footer(
    article: dict[str, Any],
    labels: dict[str, str],
) -> str:
    footer = article.get("article_footer")

    if not isinstance(footer, dict):
        return ""

    blocks = []

    if footer.get("show_meta") is True:
        blocks.append(
            render_article_meta(
                article,
                labels,
                indent="      ",
            )
        )

    blocks.append(
        render_cta(
            footer["cta"],
            "guide-article-footer-cta",
        )
    )

    return (
        '    <section class="section guide-article-footer">\n'
        '      <div class="guide-content">\n'
        + "\n\n".join(blocks)
        + '\n      </div>\n'
        '    </section>'
    )


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


def render_ordered_blocks(
    blocks: list[dict[str, Any]],
) -> str:
    rendered: list[str] = []

    for block_index, block in enumerate(blocks):
        block_type = block["type"]

        if block_type == "paragraph":
            next_block = (
                blocks[block_index + 1]
                if block_index + 1 < len(blocks)
                else None
            )
            is_list_heading = (
                isinstance(next_block, dict)
                and next_block.get("type") == "checklist"
                and block["text"].rstrip().endswith(":")
            )

            if is_list_heading:
                rendered.append(
                    '        <p class="guide-list-heading">'
                    f'{escape_text(block["text"])}</p>'
                )
            else:
                rendered.append(
                    render_paragraphs([block["text"]])
                )
        elif block_type == "checklist":
            rendered.append(
                render_checklist(block["items"])
            )
        elif block_type == "subheading":
            rendered.append(
                f"        <h3>{escape_text(block['text'])}</h3>"
            )
        else:
            raise ValueError(
                f"UNSUPPORTED_ORDERED_BLOCK_TYPE: {block_type}"
            )

    return "\n\n".join(rendered)


def render_section(section: dict[str, Any]) -> str:
    blocks: list[str] = []

    if "blocks" in section:
        blocks.append(
            render_ordered_blocks(section["blocks"])
        )
    else:
        if section.get("paragraphs"):
            blocks.append(
                render_paragraphs(section["paragraphs"])
            )

        if section.get("items"):
            blocks.append(
                render_items(section["items"])
            )

        if section.get("checklist"):
            blocks.append(
                render_checklist(section["checklist"])
            )

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
    eyebrow: str = "Perguntas frequentes",
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
        f'          <p class="eyebrow">{escape_text(eyebrow)}</p>\n'
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
    eyebrow: str = "Continuar",
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
        f'          <p class="eyebrow">{escape_text(eyebrow)}</p>\n'
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
    labels = guide_render_labels(article["locale"])
    url = public_url(
        registry["base_url"],
        article["path"],
    )
    social_preview = article.get("social_preview")
    image_path = (
        social_preview["image"]
        if isinstance(social_preview, dict)
        else "/assets/brand/og-image-v8.jpg"
    )
    image_url = (
        registry["base_url"].rstrip("/")
        + image_path
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
                "item": (
                    registry["base_url"].rstrip("/")
                    + labels["home_href"]
                ),
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": labels["guides"],
                "item": public_url(
                    registry["base_url"],
                    (
                        labels["guides_href"]
                        if article["locale"] in {"en", "ru"}
                        else registry["guides_hub"]
                    ),
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
    social_preview = article.get("social_preview")

    if isinstance(social_preview, dict):
        social_title = social_preview["title"]
        social_description = social_preview["description"]
        social_image_path = social_preview["image"]
    else:
        social_title = article["meta_title"]
        social_description = article["meta_description"]
        social_image_path = "/assets/brand/og-image-v8.jpg"

    image_url = (
        registry["base_url"].rstrip("/")
        + social_image_path
    )
    social_locale = {
        "pt-PT": "pt_PT",
        "pt-BR": "pt_BR",
        "en": "en_US",
        "ru": "ru_RU",
    }[article["locale"]]

    labels = guide_render_labels(article["locale"])
    locale_switcher = render_locale_switcher(article)
    article_footer_html = render_article_footer(
        article,
        labels,
    )
    hero_meta_html = ""

    if not isinstance(article.get("article_footer"), dict):
        hero_meta_html = render_article_meta(
            article,
            labels,
            indent="        ",
        )

    hreflang_links = render_hreflang_links(
        article,
        registry["base_url"],
        url,
    )

    article_schema, breadcrumb_schema, faq_schema = (
        build_structured_data(article, registry)
    )

    sections_for_render = article["sections"]
    verbatim_intro: str | None = None

    if article.get("intro_from_first_block") is True:
        if article.get("content_mode") != "verbatim":
            raise ValueError(
                "INTRO_FROM_FIRST_BLOCK_REQUIRES_VERBATIM"
            )

        if not sections_for_render:
            raise ValueError(
                "INTRO_FROM_FIRST_BLOCK_REQUIRES_SECTIONS"
            )

        first_section = sections_for_render[0]
        first_blocks = first_section.get("blocks")

        if (
            not isinstance(first_blocks, list)
            or not first_blocks
            or first_blocks[0].get("type") != "paragraph"
        ):
            raise ValueError(
                "INTRO_FROM_FIRST_BLOCK_REQUIRES_FIRST_PARAGRAPH"
            )

        verbatim_intro = first_blocks[0]["text"]

        first_section_without_intro = dict(first_section)
        first_section_without_intro["blocks"] = (
            first_blocks[1:]
        )

        sections_for_render = [
            first_section_without_intro,
            *sections_for_render[1:],
        ]

    section_html = "\n\n".join(
        render_section(section)
        for section in sections_for_render
    )

    key_points = "\n".join(
        f"          <li>{escape_text(item)}</li>"
        for item in article["key_points"]
    )

    rendered = f'''<!doctype html>
<html lang="{escape_text(article["locale"])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape_text(article["meta_title"])}</title>
  <meta name="description" content="{escape_text(article["meta_description"])}">
  <link rel="canonical" href="{escape_text(url)}">
{hreflang_links}
  <meta property="og:type" content="article">
  <meta property="og:site_name" content="CargoPT">
  <meta property="og:locale" content="{escape_text(social_locale)}">
  <meta property="og:title" content="{escape_text(social_title)}">
  <meta property="og:description" content="{escape_text(social_description)}">
  <meta property="og:url" content="{escape_text(url)}">
  <meta property="og:image" content="{escape_text(image_url)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape_text(social_title)}">
  <meta name="twitter:description" content="{escape_text(social_description)}">
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
  <link rel="stylesheet" href="/assets/css/components.css?v=reduced-motion-v2">
  <link rel="stylesheet" href="/assets/css/landing.css?v=reduced-motion-v2">
  <link rel="stylesheet" href="/assets/css/guides.css?v=guides-v4">
</head>
<body data-locale="{escape_text(labels["body_locale"])}" class="guide-page">
  <header class="site-header">
    <a class="logo" href="{escape_text(labels["home_href"])}" aria-label="CargoPT"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></a>
    <nav class="header-actions" aria-label="Navigation">
{locale_switcher}
      <a class="button button-small button-carrier" href="/#request">{escape_text(labels["request"])}</a>
    </nav>
  </header>

  <main id="top">
    <nav class="section guide-breadcrumb" aria-label="Breadcrumb">
      <a href="{escape_text(labels["home_href"])}">CargoPT</a>
      <span aria-hidden="true">→</span>
      <a href="{escape_text(labels["guides_href"])}">{escape_text(labels["guides"])}</a>
      <span aria-hidden="true">→</span>
      <span aria-current="page">{escape_text(article["title"])}</span>
    </nav>

    <header class="section guide-hero">
      <div class="guide-content">
        <p class="eyebrow">{escape_text(article["eyebrow"])}</p>
        <h1>{escape_text(article["title"])}</h1>
        <p class="hero-text">{escape_text(article["hero_description"])}</p>
{hero_meta_html}
      </div>
    </header>

    <section class="section guide-section guide-direct-answer">
      <div class="guide-content">
        <div class="section-heading">
          <p class="eyebrow">{escape_text(labels["direct_answer"])}</p>
          <h2>{escape_text(article["direct_answer_heading"])}</h2>
        </div>
        <p>{escape_text(article["direct_answer"])}</p>
      </div>
    </section>

    <section class="section guide-section">
      <div class="guide-content">
        <div class="section-heading">
          <p class="eyebrow">{escape_text(labels["key_points"])}</p>
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
    labels["faq"],
)}

{render_related_links(
    article["related_links"],
    article["related_links_heading"],
    labels["continue"],
)}

{render_cta(article["final_cta"], "final-cta guide-final-cta")}

{article_footer_html}
  </main>

  <footer class="site-footer">
    <div class="footer-brand">
      <strong class="footer-logo"><span class="logo-cargo">Cargo</span><span class="logo-pt">PT</span></strong>
    </div>
    <nav class="footer-links" aria-label="{escape_text(labels["footer_aria"])}">
      <a href="{escape_text(labels["footer_carriers_href"])}">{escape_text(labels["footer_carriers"])}</a>
      <a href="{escape_text(labels["footer_privacy_href"])}">{escape_text(labels["footer_privacy"])}</a>
      <a href="{escape_text(labels["footer_terms_href"])}">{escape_text(labels["footer_terms"])}</a>
      <a href="{escape_text(labels["footer_cookies_href"])}">{escape_text(labels["footer_cookies"])}</a>
      <a href="mailto:hello@cargopt.pt">{escape_text(labels["footer_contact"])}</a>
    </nav>
  </footer>
</body>
</html>
'''

    if article.get("content_mode") != "verbatim":
        return rendered

    faq_schema_line = (
        '  <script type="application/ld+json">'
        f'{json_ld(faq_schema)}</script>\n'
    )
    rendered = rendered.replace(faq_schema_line, "", 1)

    hero_eyebrow = (
        '        <p class="eyebrow">'
        f'{escape_text(article["eyebrow"])}</p>\n'
    )
    rendered = rendered.replace(hero_eyebrow, "", 1)

    hero_description = (
        '        <p class="hero-text">'
        f'{escape_text(article["hero_description"])}</p>\n'
    )
    rendered = rendered.replace(hero_description, "", 1)

    if verbatim_intro is not None:
        hero_heading = (
            f'        <h1>{escape_text(article["title"])}</h1>\n'
        )
        hero_intro = (
            '        <p class="guide-intro">'
            f'{escape_text(verbatim_intro)}</p>\n'
        )

        if rendered.count(hero_heading) != 1:
            raise ValueError(
                "VERBATIM_HERO_HEADING_NOT_UNIQUE"
            )

        rendered = rendered.replace(
            hero_heading,
            hero_heading + hero_intro,
            1,
        )

    body_start = rendered.index(
        '    <section class="section guide-section '
        'guide-direct-answer">\n'
    )

    final_cta_html = render_cta(
        article["final_cta"],
        "final-cta guide-final-cta",
    )
    body_end = (
        rendered.index(final_cta_html, body_start)
        + len(final_cta_html)
    )

    rendered = (
        rendered[:body_start]
        + section_html
        + rendered[body_end:]
    )

    return rendered


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
