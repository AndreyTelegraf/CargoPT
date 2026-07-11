from xml.etree import ElementTree

from scripts.guide_sitemap_update import add_guide_to_sitemap


URL = (
    "https://cargopt.pt/guias/precos/"
    "quanto-custa-mudanca-lisboa/"
)


def base_sitemap() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/'
        'schemas/sitemap/0.9">\n'
        '  <url><loc>https://cargopt.pt/guias/</loc>'
        '<lastmod>2026-07-11</lastmod></url>\n'
        '</urlset>\n'
    )


def require_failure(callback, expected_message: str) -> None:
    try:
        callback()
    except ValueError as error:
        if expected_message not in str(error):
            raise AssertionError(
                f"unexpected error: {error}"
            ) from error
    else:
        raise AssertionError(
            f"expected ValueError containing "
            f"{expected_message!r}"
        )


def exercise_success() -> None:
    original = base_sitemap()

    updated = add_guide_to_sitemap(
        original,
        url=URL,
        last_modified="2026-07-11",
    )

    if original != base_sitemap():
        raise AssertionError("source sitemap was mutated")

    if updated.count(URL) != 1:
        raise AssertionError("guide URL count is not one")

    expected_entry = (
        f"  <url><loc>{URL}</loc>"
        "<lastmod>2026-07-11</lastmod></url>\n"
    )

    if expected_entry not in updated:
        raise AssertionError("expected sitemap entry missing")

    if not updated.endswith("</urlset>\n"):
        raise AssertionError("closing urlset format changed")

    ElementTree.fromstring(updated)


def exercise_duplicate_failure() -> None:
    existing = base_sitemap().replace(
        "</urlset>\n",
        (
            f"  <url><loc>{URL}</loc>"
            "<lastmod>2026-07-11</lastmod></url>\n"
            "</urlset>\n"
        ),
    )

    require_failure(
        lambda: add_guide_to_sitemap(
            existing,
            url=URL,
            last_modified="2026-07-11",
        ),
        "Guide URL must be absent before publication, found 1",
    )


def exercise_duplicate_twice_failure() -> None:
    entry = (
        f"  <url><loc>{URL}</loc>"
        "<lastmod>2026-07-11</lastmod></url>\n"
    )
    existing = base_sitemap().replace(
        "</urlset>\n",
        entry + entry + "</urlset>\n",
    )

    require_failure(
        lambda: add_guide_to_sitemap(
            existing,
            url=URL,
            last_modified="2026-07-11",
        ),
        "Guide URL must be absent before publication, found 2",
    )


def exercise_invalid_xml_failure() -> None:
    try:
        add_guide_to_sitemap(
            "<urlset>\n",
            url=URL,
            last_modified="2026-07-11",
        )
    except ElementTree.ParseError:
        return

    raise AssertionError("expected XML parse failure")


def exercise_closing_format_failure() -> None:
    invalid = base_sitemap().removesuffix("\n")

    require_failure(
        lambda: add_guide_to_sitemap(
            invalid,
            url=URL,
            last_modified="2026-07-11",
        ),
        "Sitemap must end with </urlset> followed by newline",
    )


def main() -> None:
    exercise_success()
    exercise_duplicate_failure()
    exercise_duplicate_twice_failure()
    exercise_invalid_xml_failure()
    exercise_closing_format_failure()

    print("GUIDE_SITEMAP_UPDATE_SMOKE_OK")


if __name__ == "__main__":
    main()
