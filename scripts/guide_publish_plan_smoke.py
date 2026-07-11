import copy
import json
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.guide_publish_plan import build_publication_plan
from scripts.render_guide import public_url


SOURCE_ARTICLE_PATH = (
    PROJECT_ROOT
    / "content/guides/articles/quanto-custa-uma-mudanca.json"
)
SOURCE_REGISTRY_PATH = (
    PROJECT_ROOT
    / "content/guides/topics.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def topic_for(
    registry: dict,
    article_id: str,
) -> dict:
    matches = [
        topic
        for topic in registry["topics"]
        if topic["id"] == article_id
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"expected one topic, got {len(matches)}"
        )

    return matches[0]


def source_data(status: str) -> tuple[dict, dict]:
    article = copy.deepcopy(load_json(SOURCE_ARTICLE_PATH))
    registry = copy.deepcopy(load_json(SOURCE_REGISTRY_PATH))

    topic_for(
        registry,
        article["id"],
    )["status"] = status

    return article, registry


def base_sitemap() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/'
        'schemas/sitemap/0.9">\n'
        '  <url><loc>https://cargopt.pt/guias/</loc>'
        '<lastmod>2026-07-11</lastmod></url>\n'
        '</urlset>\n'
    )

def require_failure(
    callback,
    expected_message: str,
) -> None:
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


def exercise_success(status: str) -> None:
    article, registry = source_data(status)

    original_article = copy.deepcopy(article)
    original_registry = copy.deepcopy(registry)
    original_sitemap = base_sitemap()

    with tempfile.TemporaryDirectory(
        prefix=f"guide-publish-plan-{status}-"
    ) as temp_dir:
        static_root = Path(temp_dir) / "static"
        static_root.mkdir()

        plan = build_publication_plan(
            article=article,
            registry=registry,
            sitemap_text=original_sitemap,
            static_root=static_root,
        )

        expected_url = public_url(
            registry["base_url"],
            article["path"],
        )

        if plan.article_id != article["id"]:
            raise AssertionError("article id differs")

        if plan.public_url != expected_url:
            raise AssertionError("public URL differs")

        if plan.output_path.exists():
            raise AssertionError(
                "read-only plan created public HTML"
            )

        if not plan.rendered_html.startswith(
            "<!doctype html>\n"
        ):
            raise AssertionError("rendered doctype missing")

        if not plan.rendered_html.endswith("</html>\n"):
            raise AssertionError(
                "rendered closing html missing"
            )

        updated_registry = json.loads(plan.registry_text)
        updated_topic = topic_for(
            updated_registry,
            article["id"],
        )

        if updated_topic["status"] != "published":
            raise AssertionError(
                f"unexpected planned status: "
                f"{updated_topic['status']}"
            )

        if plan.sitemap_text.count(expected_url) != 1:
            raise AssertionError(
                "planned sitemap URL count is not one"
            )

        ElementTree.fromstring(plan.sitemap_text)

        if article != original_article:
            raise AssertionError("article input was mutated")

        if registry != original_registry:
            raise AssertionError("registry input was mutated")

        if original_sitemap != base_sitemap():
            raise AssertionError(
                "source sitemap changed unexpectedly"
            )


def exercise_existing_output_failure() -> None:
    article, registry = source_data("planned")

    with tempfile.TemporaryDirectory(
        prefix="guide-publish-plan-output-"
    ) as temp_dir:
        static_root = Path(temp_dir) / "static"
        output_path = (
            static_root
            / article["path"].strip("/")
            / "index.html"
        )
        output_path.parent.mkdir(parents=True)
        output_path.write_text(
            "existing\n",
            encoding="utf-8",
        )

        require_failure(
            lambda: build_publication_plan(
                article=article,
                registry=registry,
                sitemap_text=base_sitemap(),
                static_root=static_root,
            ),
            "Guide output already exists before publication",
        )


def exercise_published_failure() -> None:
    article, registry = source_data("published")

    with tempfile.TemporaryDirectory(
        prefix="guide-publish-plan-published-"
    ) as temp_dir:
        require_failure(
            lambda: build_publication_plan(
                article=article,
                registry=registry,
                sitemap_text=base_sitemap(),
                static_root=Path(temp_dir),
            ),
            "requires planned or draft status",
        )


def exercise_duplicate_sitemap_failure() -> None:
    article, registry = source_data("planned")
    url = public_url(
        registry["base_url"],
        article["path"],
    )

    entry = (
        f"  <url><loc>{url}</loc>"
        "<lastmod>2026-07-11</lastmod></url>\n"
    )
    sitemap = base_sitemap().replace(
        "</urlset>\n",
        entry + "</urlset>\n",
    )

    with tempfile.TemporaryDirectory(
        prefix="guide-publish-plan-duplicate-"
    ) as temp_dir:
        require_failure(
            lambda: build_publication_plan(
                article=article,
                registry=registry,
                sitemap_text=sitemap,
                static_root=Path(temp_dir),
            ),
            "Guide URL must be absent before publication",
        )


def exercise_contract_failure() -> None:
    article, registry = source_data("planned")
    article["title"] = "Different title"

    with tempfile.TemporaryDirectory(
        prefix="guide-publish-plan-contract-"
    ) as temp_dir:
        require_failure(
            lambda: build_publication_plan(
                article=article,
                registry=registry,
                sitemap_text=base_sitemap(),
                static_root=Path(temp_dir),
            ),
            "Article and registry differ for title",
        )


def main() -> None:
    exercise_success("planned")
    exercise_success("draft")
    exercise_existing_output_failure()
    exercise_published_failure()
    exercise_duplicate_sitemap_failure()
    exercise_contract_failure()

    print("GUIDE_PUBLISH_PLAN_SMOKE_OK")


if __name__ == "__main__":
    main()
