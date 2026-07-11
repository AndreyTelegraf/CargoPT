import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.render_guide import output_path_for_article
from scripts.render_guide import public_url
from scripts.render_guide import render_guide


PREFLIGHT_PATH = PROJECT_ROOT / "scripts/guide_publish_preflight.py"
SOURCE_ARTICLE_PATH = (
    PROJECT_ROOT
    / "content/guides/articles/quanto-custa-uma-mudanca.json"
)
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "content/guides/topics.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_sitemap(path: Path, urls: list[str]) -> None:
    entries = "\n".join(
        f"  <url><loc>{escape(url)}</loc></url>"
        for url in urls
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )
    path.write_text(body, encoding="utf-8")


def set_topic_status(
    registry: dict[str, Any],
    article_id: str,
    status: str,
) -> None:
    matches = [
        topic
        for topic in registry["topics"]
        if topic["id"] == article_id
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"expected one topic for {article_id!r}, got {len(matches)}"
        )

    matches[0]["status"] = status


def run_preflight(
    *,
    article_path: Path,
    registry_path: Path,
    sitemap_path: Path,
    static_root: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(PREFLIGHT_PATH),
            str(article_path),
            "--registry",
            str(registry_path),
            "--sitemap",
            str(sitemap_path),
            "--static-root",
            str(static_root),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def require_success(
    result: subprocess.CompletedProcess[str],
    *,
    expected_status: str,
) -> None:
    if result.returncode != 0:
        raise AssertionError(
            f"expected success for {expected_status}, "
            f"got exit {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    expected_tokens = (
        "GUIDE_PUBLISH_PREFLIGHT_OK",
        expected_status,
    )

    for token in expected_tokens:
        if token not in result.stdout:
            raise AssertionError(
                f"missing {token!r} in stdout:\n{result.stdout}"
            )


def require_failure(
    result: subprocess.CompletedProcess[str],
    *,
    expected_message: str,
) -> None:
    if result.returncode == 0:
        raise AssertionError(
            "expected failure, got success\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    combined = result.stdout + result.stderr

    if expected_message not in combined:
        raise AssertionError(
            f"missing failure message {expected_message!r}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )


def prepare_case(
    root: Path,
    *,
    status: str,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    Path,
    Path,
    Path,
    Path,
]:
    article = copy.deepcopy(load_json(SOURCE_ARTICLE_PATH))
    registry = copy.deepcopy(load_json(SOURCE_REGISTRY_PATH))
    set_topic_status(registry, article["id"], status)

    article_path = root / "article.json"
    registry_path = root / "topics.json"
    sitemap_path = root / "sitemap.xml"
    static_root = root / "static"

    static_root.mkdir(parents=True)

    write_json(article_path, article)
    write_json(registry_path, registry)

    return (
        article,
        registry,
        article_path,
        registry_path,
        sitemap_path,
        static_root,
    )


def exercise_unpublished_status(status: str) -> None:
    with tempfile.TemporaryDirectory(
        prefix=f"guide-preflight-{status}-"
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

        url = public_url(registry["base_url"], article["path"])
        write_sitemap(sitemap_path, [])

        output_path = output_path_for_article(article, static_root)

        if output_path.exists():
            raise AssertionError(
                f"unexpected output before preflight: {output_path}"
            )

        result = run_preflight(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_success(result, expected_status=status)

        if output_path.exists():
            raise AssertionError(
                f"preflight wrote public HTML: {output_path}"
            )

        if url in sitemap_path.read_text(encoding="utf-8"):
            raise AssertionError(
                f"preflight changed sitemap unexpectedly: {url}"
            )


def exercise_published_success() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-preflight-published-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            article,
            registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status="published")

        url = public_url(registry["base_url"], article["path"])
        write_sitemap(sitemap_path, [url])

        output_path = output_path_for_article(article, static_root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_guide(article, registry),
            encoding="utf-8",
        )

        before_html = output_path.read_bytes()
        before_sitemap = sitemap_path.read_bytes()

        result = run_preflight(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_success(result, expected_status="published")

        if output_path.read_bytes() != before_html:
            raise AssertionError("preflight changed published HTML")

        if sitemap_path.read_bytes() != before_sitemap:
            raise AssertionError("preflight changed sitemap")


def exercise_published_html_mismatch() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-preflight-mismatch-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            article,
            registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status="published")

        url = public_url(registry["base_url"], article["path"])
        write_sitemap(sitemap_path, [url])

        output_path = output_path_for_article(article, static_root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_guide(article, registry) + "<!-- mismatch -->\n",
            encoding="utf-8",
        )

        result = run_preflight(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_failure(
            result,
            expected_message=(
                "Published HTML differs from renderer output"
            ),
        )


def exercise_published_duplicate_sitemap_url() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-preflight-duplicate-"
    ) as temp_dir:
        root = Path(temp_dir)
        (
            article,
            registry,
            article_path,
            registry_path,
            sitemap_path,
            static_root,
        ) = prepare_case(root, status="published")

        url = public_url(registry["base_url"], article["path"])
        write_sitemap(sitemap_path, [url, url])

        output_path = output_path_for_article(article, static_root)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            render_guide(article, registry),
            encoding="utf-8",
        )

        result = run_preflight(
            article_path=article_path,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
            static_root=static_root,
        )

        require_failure(
            result,
            expected_message=(
                "Published guide URL must appear exactly once "
                "in sitemap, found 2"
            ),
        )


def main() -> None:
    exercise_unpublished_status("planned")
    exercise_unpublished_status("draft")
    exercise_published_success()
    exercise_published_html_mismatch()
    exercise_published_duplicate_sitemap_url()

    print("GUIDE_PUBLISH_PREFLIGHT_SMOKE_OK")


if __name__ == "__main__":
    main()
