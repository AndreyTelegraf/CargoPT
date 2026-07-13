import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = PROJECT_ROOT / "content/guides/internal-link-map.json"
DEFAULT_REGISTRY = PROJECT_ROOT / "content/guides/topics.json"
DEFAULT_ARTICLES_DIR = PROJECT_ROOT / "content/guides/articles"
DEFAULT_AUDITOR = PROJECT_ROOT / "scripts/corpus_release_audit.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the canonical CargoPT internal link map "
            "to structured guide articles."
        )
    )
    parser.add_argument(
        "--map",
        type=Path,
        default=DEFAULT_MAP,
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
    )
    parser.add_argument(
        "--articles-dir",
        type=Path,
        default=DEFAULT_ARTICLES_DIR,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and print the plan without writing files.",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()

    link_map = load_json(args.map)
    registry = load_json(args.registry)

    if link_map.get("schema_version") != 2:
        raise SystemExit("INVALID_LINK_MAP_SCHEMA")

    links = link_map.get("links")
    request_target = link_map.get("request_target")

    if not isinstance(links, dict):
        raise SystemExit("INVALID_LINK_MAP_LINKS")

    if not isinstance(request_target, dict):
        raise SystemExit("INVALID_REQUEST_TARGET")

    topics = registry.get("topics")

    if not isinstance(topics, list):
        raise SystemExit("INVALID_REGISTRY_TOPICS")

    topics_by_id = {
        topic["id"]: topic
        for topic in topics
        if isinstance(topic, dict)
        and isinstance(topic.get("id"), str)
    }

    article_paths: dict[str, Path] = {}
    articles: dict[str, dict[str, Any]] = {}

    for path in sorted(args.articles_dir.glob("*.json")):
        article = load_json(path)
        article_id = article.get("id")

        if not isinstance(article_id, str):
            raise SystemExit(
                f"INVALID_ARTICLE_ID={path}"
            )

        article_paths[article_id] = path
        articles[article_id] = article

    if set(links) != set(articles):
        raise SystemExit(
            "LINK_MAP_ARTICLE_SET_MISMATCH="
            f"missing={sorted(set(articles) - set(links))}:"
            f"extra={sorted(set(links) - set(articles))}"
        )

    planned_updates: list[
        tuple[Path, dict[str, Any], list[dict[str, str]]]
    ] = []
    rendered_by_id: dict[str, list[dict[str, str]]] = {}

    for source_id in sorted(links):
        relationships = links[source_id]

        if not isinstance(relationships, list):
            raise SystemExit(
                f"INVALID_RELATIONSHIP_LIST={source_id}"
            )

        if len(relationships) != 4:
            raise SystemExit(
                "INVALID_RELATIONSHIP_COUNT="
                f"{source_id}:{len(relationships)}"
            )

        ordered_targets: list[tuple[int, str]] = []

        for relationship in relationships:
            if not isinstance(relationship, dict):
                raise SystemExit(
                    f"INVALID_RELATIONSHIP="
                    f"{source_id}:{relationship!r}"
                )

            target_id = relationship.get("target")
            priority = relationship.get("priority")

            if not isinstance(target_id, str) or not target_id:
                raise SystemExit(
                    "INVALID_RELATIONSHIP_TARGET="
                    f"{source_id}:{relationship!r}"
                )

            if (
                not isinstance(priority, int)
                or isinstance(priority, bool)
            ):
                raise SystemExit(
                    "INVALID_RELATIONSHIP_PRIORITY="
                    f"{source_id}:{relationship!r}"
                )

            ordered_targets.append((priority, target_id))

        ordered_targets.sort(key=lambda item: item[0])

        priorities = [
            priority
            for priority, _ in ordered_targets
        ]

        if priorities != [1, 2, 3, 4]:
            raise SystemExit(
                "INVALID_PRIORITY_SEQUENCE="
                f"{source_id}:{priorities}"
            )

        target_ids = [
            target_id
            for _, target_id in ordered_targets
        ]

        if len(set(target_ids)) != 4:
            raise SystemExit(
                f"DUPLICATE_TARGET={source_id}:{target_ids}"
            )

        if source_id in target_ids:
            raise SystemExit(
                f"SELF_TARGET={source_id}"
            )

        rendered_links: list[dict[str, str]] = []

        for target_id in target_ids:
            if target_id == request_target.get("id"):
                rendered_links.append(
                    {
                        "title": request_target["title"],
                        "href": request_target["href"],
                        "type": request_target["type"],
                    }
                )
                continue

            topic = topics_by_id.get(target_id)

            if topic is None:
                raise SystemExit(
                    f"UNKNOWN_TARGET={source_id}:{target_id}"
                )

            status = topic.get("status")

            if status == "published":
                link_type = "guide"
            elif status == "planned":
                link_type = "planned"
            elif status == "existing_landing":
                link_type = "landing"
            else:
                raise SystemExit(
                    f"UNSUPPORTED_TARGET_STATUS="
                    f"{target_id}:{status}"
                )

            rendered_links.append(
                {
                    "title": topic["title"],
                    "href": topic["path"],
                    "type": link_type,
                }
            )

        rendered_by_id[source_id] = rendered_links

        article = articles[source_id]
        current_links = article.get("related_links")

        if current_links != rendered_links:
            planned_updates.append(
                (
                    article_paths[source_id],
                    article,
                    rendered_links,
                )
            )

        print(
            f"{source_id}: "
            f"{len(rendered_links)} links "
            f"{'CHANGE' if current_links != rendered_links else 'UNCHANGED'}"
        )

    print(f"ARTICLE_COUNT={len(articles)}")
    print(f"PLANNED_UPDATES={len(planned_updates)}")

    if not DEFAULT_AUDITOR.is_file():
        raise SystemExit(
            f"MISSING_CORPUS_AUDITOR={DEFAULT_AUDITOR}"
        )

    with tempfile.TemporaryDirectory(
        prefix="cargopt-link-map-preflight-"
    ) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        text_report = temp_dir / "audit.txt"
        json_report = temp_dir / "audit.json"

        for article_id, article in articles.items():
            candidate = dict(article)
            candidate["related_links"] = rendered_by_id[article_id]

            candidate_path = temp_dir / article_paths[article_id].name
            candidate_path.write_text(
                json.dumps(
                    candidate,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

        command = [
            sys.executable,
            str(DEFAULT_AUDITOR),
            "--registry",
            str(args.registry),
            "--articles-dir",
            str(temp_dir),
            "--text-report",
            str(text_report),
            "--json-report",
            str(json_report),
        ]

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        print("===== CORPUS PREFLIGHT STDOUT =====")
        print(result.stdout, end="")

        if result.stderr:
            print("===== CORPUS PREFLIGHT STDERR =====")
            print(result.stderr, end="")

        if result.returncode != 0:
            raise SystemExit(
                "INTERNAL_LINK_MAP_PREFLIGHT_FAILED="
                f"{result.returncode}"
            )

        print("INTERNAL_LINK_MAP_PREFLIGHT_OK")

    if args.check:
        print("INTERNAL_LINK_MAP_CHECK_OK")
        return

    for path, article, rendered_links in planned_updates:
        article["related_links"] = rendered_links
        path.write_text(
            json.dumps(
                article,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"UPDATED {path}")

    print(
        f"APPLIED_UPDATES={len(planned_updates)}"
    )
    print("INTERNAL_LINK_MAP_APPLY_OK")


if __name__ == "__main__":
    main()
