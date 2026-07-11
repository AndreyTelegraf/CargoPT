import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.render_guide import output_path_for_article
from scripts.render_guide import public_url


PUBLISHER_PATH = PROJECT_ROOT / "scripts/publish_guide.py"
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


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


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


def prepare_case(
    root: Path,
    *,
    status: str,
) -> tuple[
    dict,
    dict,
    Path,
    Path,
    Path,
    Path,
]:
    article = copy.deepcopy(load_json(SOURCE_ARTICLE_PATH))
    registry = copy.deepcopy(load_json(SOURCE_REGISTRY_PATH))
    topic_for(registry, article["id"])["status"] = status

    article_path = root / "article.json"
    registry_path = root / "topics.json"
    sitemap_path = root / "sitemap.xml"
    static_root = root / "static"

    static_root.mkdir(parents=True)

    write_json(article_path, article)
    write_json(registry_path, registry)

    sitemap_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/'
        'schemas/sitemap/0.9">\n'
        '  <url><loc>https://cargopt.pt/guias/</loc>'
        '<lastmod>2026-07-11</lastmod></url>\n'
        '</urlset>\n',
        encoding="utf-8",
    )

    return (
        article,
        registry,
        article_path,
        registry_path,
        sitemap_path,
        static_root,
    )


def run_publisher(
    *,
    article_path: Path,
    registry_path: Path,
    sitemap_path: Path,
    static_root: Path,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(PUBLISHER_PATH),
        str(article_path),
        "--registry",
        str(registry_path),
        "--sitemap",
        str(sitemap_path),
        "--static-root",
        str(static_root),
    ]

    if check:
        command.append("--check")

    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def require_success(
    result: subprocess.CompletedProcess[str],
    expected_token: str,
) -> None:
    if result.returncode != 0:
        raise AssertionError(
            f"expected success, got exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    if expected_token not in result.stdout:
        raise AssertionError(
            f"missing {expected_token!r}\n"
            f"stdout:\n{result.stdout}"
        )


def require_failure(
    result: subprocess.CompletedProcess[str],
    expected_message: str,
) -> None:
    if result.returncode == 0:
        raise AssertionError(
            "expected failure, got success\n"
            f"stdout:\n{result.stdout}"
        )

    combined = result.stdout + result.stderr

    if expected_message not in combined:
        raise AssertionError(
            f"missing failure message {expected_message!r}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def exercise_check_mode() -> None:
    with tempfile.TemporaryDirectory(
        prefix="publish-guide-check-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            article,
            registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status="planned")

        before_registry = registry_path.read_bytes()
        before_sitemap = sitemap_path.read_bytes()
        output_path = output_path_for_article(
            article,
            static_root,
        )

        result = run_publisher(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
            check=True,
        )

        require_success(
            result,
            "GUIDE_PUBLISH_CHECK_OK",
        )

        if output_path.exists():
            raise AssertionError(
                "check mode created public HTML"
            )

        if registry_path.read_bytes() != before_registry:
            raise AssertionError(
                "check mode changed registry"
            )

        if sitemap_path.read_bytes() != before_sitemap:
            raise AssertionError(
                "check mode changed sitemap"
            )

        url = public_url(
            registry["base_url"],
            article["path"],
        )

        if url in sitemap_path.read_text(encoding="utf-8"):
            raise AssertionError(
                "check mode added URL to sitemap"
            )


def exercise_publish_success(status: str) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"publish-guide-{status}-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            article,
            registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status=status)

        result = run_publisher(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_success(
            result,
            "GUIDE_PUBLISHED",
        )

        output_path = output_path_for_article(
            article,
            static_root,
        )

        if not output_path.is_file():
            raise AssertionError(
                "published HTML is missing"
            )

        published_registry = load_json(registry_path)
        published_topic = topic_for(
            published_registry,
            article["id"],
        )

        if published_topic["status"] != "published":
            raise AssertionError(
                "registry status is not published"
            )

        url = public_url(
            registry["base_url"],
            article["path"],
        )
        sitemap_text = sitemap_path.read_text(
            encoding="utf-8"
        )

        if sitemap_text.count(url) != 1:
            raise AssertionError(
                "published URL count is not one"
            )


def exercise_second_publish_failure() -> None:
    with tempfile.TemporaryDirectory(
        prefix="publish-guide-repeat-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            _article,
            _registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status="planned")

        first = run_publisher(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )
        require_success(first, "GUIDE_PUBLISHED")

        second = run_publisher(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_failure(
            second,
            "requires planned or draft status",
        )


def main() -> None:
    exercise_check_mode()
    exercise_publish_success("planned")
    exercise_publish_success("draft")
    exercise_second_publish_failure()

    print("PUBLISH_GUIDE_SMOKE_OK")


if __name__ == "__main__":
    main()
