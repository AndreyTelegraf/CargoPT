import copy
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.publish_guides_batch import apply_batch_publication_plan
from scripts.publish_guides_batch import build_batch_publication_plan


SOURCE_ARTICLE = (
    PROJECT_ROOT
    / "content/guides/articles/como-reduzir-custo-mudanca.json"
)
SOURCE_REGISTRY = PROJECT_ROOT / "content/guides/topics.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture() -> tuple[list[dict], dict, str]:
    source = load_json(SOURCE_ARTICLE)
    registry = load_json(SOURCE_REGISTRY)
    articles = []

    for number in (1, 2):
        article = copy.deepcopy(source)
        article_id = f"batch-test-{number}"
        article["id"] = article_id
        article["path"] = f"/guias/test/{article_id}/"
        article["title"] = f"Batch test {number}"
        article["meta_title"] = f"Batch test {number} — CargoPT"
        article["primary_query"] = f"batch test {number}"
        article.pop("translation_group", None)
        article.pop("alternates", None)
        articles.append(article)
        registry["topics"].append(
            {
                "id": article_id,
                "cluster": article["cluster"],
                "title": article["title"],
                "slug": article_id,
                "path": article["path"],
                "primary_query": article["primary_query"],
                "intent": article["intent"],
                "priority": 9,
                "status": "planned",
                "parent": "/guias/",
                "related": [],
            }
        )

    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url><loc>https://cargopt.pt/guias/</loc>'
        '<lastmod>2026-07-24</lastmod></url>\n'
        '</urlset>\n'
    )
    return articles, registry, sitemap


def write_shared(
    root: Path,
    registry: dict,
    sitemap: str,
) -> tuple[Path, Path, bytes, bytes]:
    registry_path = root / "content/topics.json"
    sitemap_path = root / "static/sitemap.xml"
    registry_path.parent.mkdir(parents=True)
    sitemap_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sitemap_path.write_text(sitemap, encoding="utf-8")
    return (
        registry_path,
        sitemap_path,
        registry_path.read_bytes(),
        sitemap_path.read_bytes(),
    )


def exercise_success() -> None:
    articles, registry, sitemap = fixture()

    with tempfile.TemporaryDirectory(
        prefix="guide-batch-success-"
    ) as temp_dir:
        root = Path(temp_dir)
        static_root = root / "static"
        registry_path, sitemap_path, _, _ = write_shared(
            root,
            registry,
            sitemap,
        )
        batch = build_batch_publication_plan(
            articles=articles,
            registry=registry,
            sitemap_text=sitemap,
            static_root=static_root,
        )

        if any(plan.output_path.exists() for plan in batch.plans):
            raise AssertionError("planning wrote output files")

        apply_batch_publication_plan(
            batch,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
        )

        published_registry = json.loads(
            registry_path.read_text(encoding="utf-8")
        )
        statuses = {
            topic["id"]: topic["status"]
            for topic in published_registry["topics"]
            if topic["id"].startswith("batch-test-")
        }
        if statuses != {
            "batch-test-1": "published",
            "batch-test-2": "published",
        }:
            raise AssertionError(statuses)

        for plan in batch.plans:
            if not plan.output_path.is_file():
                raise AssertionError(plan.output_path)
            if batch.sitemap_text.count(plan.public_url) != 1:
                raise AssertionError(plan.public_url)


def exercise_duplicate_preflight() -> None:
    articles, registry, sitemap = fixture()

    with tempfile.TemporaryDirectory(
        prefix="guide-batch-duplicate-"
    ) as temp_dir:
        try:
            build_batch_publication_plan(
                articles=[articles[0], copy.deepcopy(articles[0])],
                registry=registry,
                sitemap_text=sitemap,
                static_root=Path(temp_dir),
            )
        except ValueError as error:
            if "DUPLICATE_BATCH_ARTICLE_ID" not in str(error):
                raise
        else:
            raise AssertionError("duplicate batch was accepted")


def exercise_rollback() -> None:
    articles, registry, sitemap = fixture()

    with tempfile.TemporaryDirectory(
        prefix="guide-batch-rollback-"
    ) as temp_dir:
        root = Path(temp_dir)
        static_root = root / "static"
        (
            registry_path,
            sitemap_path,
            original_registry,
            original_sitemap,
        ) = write_shared(root, registry, sitemap)
        batch = build_batch_publication_plan(
            articles=articles,
            registry=registry,
            sitemap_text=sitemap,
            static_root=static_root,
        )

        module = __import__(
            "scripts.publish_guides_batch",
            fromlist=["atomic_write_text"],
        )
        real_write = module.atomic_write_text
        calls = 0

        def fail_third_write(path, text, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("simulated shared-file failure")
            return real_write(path, text, **kwargs)

        with patch(
            "scripts.publish_guides_batch.atomic_write_text",
            side_effect=fail_third_write,
        ):
            try:
                apply_batch_publication_plan(
                    batch,
                    registry_path=registry_path,
                    sitemap_path=sitemap_path,
                )
            except OSError as error:
                if str(error) != "simulated shared-file failure":
                    raise
            else:
                raise AssertionError("expected rollback failure")

        if any(plan.output_path.exists() for plan in batch.plans):
            raise AssertionError("batch outputs remained after rollback")
        if registry_path.read_bytes() != original_registry:
            raise AssertionError("registry changed after rollback")
        if sitemap_path.read_bytes() != original_sitemap:
            raise AssertionError("sitemap changed after rollback")


def exercise_acceptance_rollback() -> None:
    articles, registry, sitemap = fixture()

    with tempfile.TemporaryDirectory(
        prefix="guide-batch-acceptance-rollback-"
    ) as temp_dir:
        root = Path(temp_dir)
        static_root = root / "static"
        (
            registry_path,
            sitemap_path,
            original_registry,
            original_sitemap,
        ) = write_shared(root, registry, sitemap)
        batch = build_batch_publication_plan(
            articles=articles,
            registry=registry,
            sitemap_text=sitemap,
            static_root=static_root,
        )

        def fail_acceptance() -> None:
            raise RuntimeError("simulated acceptance failure")

        try:
            apply_batch_publication_plan(
                batch,
                registry_path=registry_path,
                sitemap_path=sitemap_path,
                acceptance=fail_acceptance,
            )
        except RuntimeError as error:
            if str(error) != "simulated acceptance failure":
                raise
        else:
            raise AssertionError("expected acceptance rollback")

        if any(plan.output_path.exists() for plan in batch.plans):
            raise AssertionError(
                "batch outputs remained after acceptance failure"
            )
        if registry_path.read_bytes() != original_registry:
            raise AssertionError(
                "registry changed after acceptance failure"
            )
        if sitemap_path.read_bytes() != original_sitemap:
            raise AssertionError(
                "sitemap changed after acceptance failure"
            )


def main() -> None:
    exercise_success()
    exercise_duplicate_preflight()
    exercise_rollback()
    exercise_acceptance_rollback()
    print("PUBLISH_GUIDES_BATCH_SMOKE_OK")


if __name__ == "__main__":
    main()
