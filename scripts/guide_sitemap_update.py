from xml.etree import ElementTree


def add_guide_to_sitemap(
    sitemap_text: str,
    *,
    url: str,
    last_modified: str,
) -> str:
    root = ElementTree.fromstring(sitemap_text)

    locations = [
        element.text
        for element in root.iter()
        if element.tag.endswith("loc")
    ]
    count = locations.count(url)

    if count != 0:
        raise ValueError(
            "Guide URL must be absent before publication, "
            f"found {count}: {url}"
        )

    closing_tag = "</urlset>\n"

    if not sitemap_text.endswith(closing_tag):
        raise ValueError(
            "Sitemap must end with </urlset> followed by newline"
        )

    entry = (
        f"  <url><loc>{url}</loc>"
        f"<lastmod>{last_modified}</lastmod></url>\n"
    )

    updated = sitemap_text.removesuffix(closing_tag)
    result = updated + entry + closing_tag

    ElementTree.fromstring(result)

    if result.count(url) != 1:
        raise ValueError(
            "Updated sitemap must contain guide URL exactly once"
        )

    return result
