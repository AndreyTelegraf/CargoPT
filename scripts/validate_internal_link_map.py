#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = PROJECT_ROOT / "content/guides/internal-link-map.json"
DEFAULT_REGISTRY = PROJECT_ROOT / "content/guides/topics.json"
DEFAULT_ARTICLES_DIR = PROJECT_ROOT / "content/guides/articles"

TRANSITIONAL_SCHEMA_VERSION = 1
CANONICAL_SCHEMA_VERSION = 2
REQUEST_TARGET_ID = "@request"
EXPECTED_RELATIONSHIP_COUNT = 4
MIN_ARTICLE_INCOMING = 2
MIN_ARTICLE_OUTGOING = 2

RELATIONSHIP_KEYS = frozenset({"target", "reason", "priority"})
ALLOWED_REASONS = frozenset(
    {
        "next_step",
        "dependency",
        "same_cluster",
        "authority",
        "commercial",
        "conversion",
        "prerequisite",
    }
)
JOURNEY_REASONS = frozenset(
    {
        "next_step",
        "dependency",
        "prerequisite",
    }
)


class ValidationError(Exception):
    pass


def fail(code: str, *parts: object) -> None:
    suffix = ":".join(str(part) for part in parts)
    if suffix:
        raise ValidationError(f"{code}:{suffix}")
    raise ValidationError(code)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the canonical CargoPT internal link map "
            "without writing any files."
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
        "--allow-v1-target-lists",
        action="store_true",
        help=(
            "Explicitly allow the transitional schema v1 format "
            "whose relationships are plain target-id lists."
        ),
    )
    return parser.parse_args()


def load_json(path: Path, label: str) -> Any:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        fail(f"MISSING_{label}", path)
    except OSError as exc:
        fail(f"READ_{label}_FAILED", path, exc)

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        fail(
            f"INVALID_{label}_JSON",
            path,
            f"line={exc.lineno}",
            f"column={exc.colno}",
        )


def require_non_empty_string(
    value: object,
    code: str,
    *context: object,
) -> str:
    if not isinstance(value, str) or not value.strip():
        fail(code, *context)
    return value


def require_exact_int(
    value: object,
    code: str,
    *context: object,
) -> int:
    if type(value) is not int:
        fail(code, *context, repr(value))
    return value


def load_registry(registry_path: Path) -> dict[str, dict[str, Any]]:
    registry = load_json(registry_path, "REGISTRY")

    if not isinstance(registry, dict):
        fail("INVALID_REGISTRY_ROOT")

    topics = registry.get("topics")
    if not isinstance(topics, list):
        fail("INVALID_REGISTRY_TOPICS")

    topics_by_id: dict[str, dict[str, Any]] = {}

    for index, topic in enumerate(topics):
        if not isinstance(topic, dict):
            fail("INVALID_REGISTRY_TOPIC", index)

        topic_id = require_non_empty_string(
            topic.get("id"),
            "INVALID_REGISTRY_TOPIC_ID",
            index,
        )

        if topic_id in topics_by_id:
            fail("DUPLICATE_REGISTRY_TOPIC_ID", topic_id)

        topics_by_id[topic_id] = topic

    return topics_by_id


def load_article_ids(articles_dir: Path) -> set[str]:
    if not articles_dir.is_dir():
        fail("MISSING_ARTICLES_DIR", articles_dir)

    paths = sorted(articles_dir.glob("*.json"))
    if not paths:
        fail("EMPTY_ARTICLE_CORPUS", articles_dir)

    article_ids: set[str] = set()

    for path in paths:
        article = load_json(path, "ARTICLE")

        if not isinstance(article, dict):
            fail("INVALID_ARTICLE_ROOT", path)

        article_id = require_non_empty_string(
            article.get("id"),
            "INVALID_ARTICLE_ID",
            path,
        )

        if article_id in article_ids:
            fail("DUPLICATE_ARTICLE_ID", article_id)

        article_ids.add(article_id)

    return article_ids


def validate_request_target(link_map: dict[str, Any]) -> None:
    request_target = link_map.get("request_target")

    if not isinstance(request_target, dict):
        fail("INVALID_REQUEST_TARGET")

    request_id = require_non_empty_string(
        request_target.get("id"),
        "INVALID_REQUEST_TARGET_ID",
    )
    if request_id != REQUEST_TARGET_ID:
        fail("UNEXPECTED_REQUEST_TARGET_ID", request_id)

    require_non_empty_string(
        request_target.get("title"),
        "INVALID_REQUEST_TARGET_TITLE",
    )
    require_non_empty_string(
        request_target.get("href"),
        "INVALID_REQUEST_TARGET_HREF",
    )

    request_type = require_non_empty_string(
        request_target.get("type"),
        "INVALID_REQUEST_TARGET_TYPE",
    )
    if request_type != "service":
        fail("UNEXPECTED_REQUEST_TARGET_TYPE", request_type)


def validate_top_level(
    link_map: Any,
    allow_v1_target_lists: bool,
) -> tuple[int, dict[str, Any]]:
    if not isinstance(link_map, dict):
        fail("INVALID_LINK_MAP_ROOT")

    schema_version = require_exact_int(
        link_map.get("schema_version"),
        "INVALID_LINK_MAP_SCHEMA_VERSION",
    )

    if schema_version == TRANSITIONAL_SCHEMA_VERSION:
        if not allow_v1_target_lists:
            fail("SCHEMA_V1_REQUIRES_ALLOW_FLAG")
    elif schema_version != CANONICAL_SCHEMA_VERSION:
        fail("UNSUPPORTED_LINK_MAP_SCHEMA", schema_version)

    require_non_empty_string(
        link_map.get("standard"),
        "INVALID_LINK_MAP_STANDARD",
    )
    validate_request_target(link_map)

    links = link_map.get("links")
    if not isinstance(links, dict):
        fail("INVALID_LINK_MAP_LINKS")

    for source_id in links:
        require_non_empty_string(
            source_id,
            "INVALID_LINK_MAP_SOURCE_ID",
            repr(source_id),
        )

    return schema_version, links


def validate_source_set(
    links: dict[str, Any],
    article_ids: set[str],
) -> None:
    source_ids = set(links)

    if source_ids != article_ids:
        missing = sorted(article_ids - source_ids)
        extra = sorted(source_ids - article_ids)
        fail(
            "LINK_MAP_ARTICLE_SET_MISMATCH",
            f"missing={missing}",
            f"extra={extra}",
        )


def validate_target_id(
    source_id: str,
    target_id: object,
    topics_by_id: dict[str, dict[str, Any]],
) -> str:
    target = require_non_empty_string(
        target_id,
        "INVALID_TARGET_ID",
        source_id,
        repr(target_id),
    )

    if target == source_id:
        fail("SELF_TARGET", source_id)

    if target != REQUEST_TARGET_ID and target not in topics_by_id:
        fail("UNKNOWN_TARGET", source_id, target)

    return target


def validate_v1_links(
    links: dict[str, Any],
    topics_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}

    for source_id in sorted(links):
        raw_targets = links[source_id]

        if not isinstance(raw_targets, list):
            fail("INVALID_V1_TARGET_LIST", source_id)

        if len(raw_targets) != EXPECTED_RELATIONSHIP_COUNT:
            fail(
                "INVALID_TARGET_COUNT",
                source_id,
                len(raw_targets),
            )

        targets = [
            validate_target_id(source_id, target, topics_by_id)
            for target in raw_targets
        ]

        if len(set(targets)) != len(targets):
            fail("DUPLICATE_TARGET", source_id, targets)

        normalized[source_id] = targets

    return normalized


def validate_canonical_relationships(
    links: dict[str, Any],
    topics_by_id: dict[str, dict[str, Any]],
) -> dict[str, list[str]]:
    normalized: dict[str, list[str]] = {}

    for source_id in sorted(links):
        raw_relationships = links[source_id]

        if not isinstance(raw_relationships, list):
            fail("INVALID_RELATIONSHIP_LIST", source_id)

        if len(raw_relationships) != EXPECTED_RELATIONSHIP_COUNT:
            fail(
                "INVALID_RELATIONSHIP_COUNT",
                source_id,
                len(raw_relationships),
            )

        targets: list[str] = []
        reasons: list[str] = []
        priorities: list[int] = []

        for index, relationship in enumerate(raw_relationships):
            if not isinstance(relationship, dict):
                fail(
                    "INVALID_RELATIONSHIP_OBJECT",
                    source_id,
                    index,
                )

            keys = set(relationship)
            if keys != RELATIONSHIP_KEYS:
                missing = sorted(RELATIONSHIP_KEYS - keys)
                extra = sorted(keys - RELATIONSHIP_KEYS)
                fail(
                    "INVALID_RELATIONSHIP_KEYS",
                    source_id,
                    index,
                    f"missing={missing}",
                    f"extra={extra}",
                )

            target = validate_target_id(
                source_id,
                relationship.get("target"),
                topics_by_id,
            )
            reason = require_non_empty_string(
                relationship.get("reason"),
                "INVALID_RELATIONSHIP_REASON",
                source_id,
                index,
            )
            priority = require_exact_int(
                relationship.get("priority"),
                "INVALID_RELATIONSHIP_PRIORITY",
                source_id,
                index,
            )

            if reason not in ALLOWED_REASONS:
                fail(
                    "UNKNOWN_RELATIONSHIP_REASON",
                    source_id,
                    reason,
                )

            targets.append(target)
            reasons.append(reason)
            priorities.append(priority)

        if len(set(targets)) != len(targets):
            fail("DUPLICATE_TARGET", source_id, targets)

        if len(set(reasons)) != len(reasons):
            fail("DUPLICATE_RELATIONSHIP_REASON", source_id, reasons)

        expected_priorities = list(
            range(1, EXPECTED_RELATIONSHIP_COUNT + 1)
        )
        if priorities != expected_priorities:
            fail(
                "INVALID_PRIORITY_SEQUENCE",
                source_id,
                f"expected={expected_priorities}",
                f"actual={priorities}",
            )

        reason_counts = Counter(reasons)

        if reason_counts["conversion"] != 1:
            fail(
                "INVALID_CONVERSION_COUNT",
                source_id,
                reason_counts["conversion"],
            )

        for target, reason in zip(targets, reasons):
            if reason == "conversion" and target != REQUEST_TARGET_ID:
                fail(
                    "CONVERSION_TARGET_MUST_BE_REQUEST",
                    source_id,
                    target,
                )

            if target == REQUEST_TARGET_ID and reason != "conversion":
                fail(
                    "REQUEST_TARGET_REQUIRES_CONVERSION",
                    source_id,
                    reason,
                )

        if reason_counts["same_cluster"] < 1:
            fail("MISSING_SAME_CLUSTER_REASON", source_id)

        if not JOURNEY_REASONS.intersection(reasons):
            fail("MISSING_JOURNEY_REASON", source_id)

        if reason_counts["authority"] > 1:
            fail(
                "TOO_MANY_AUTHORITY_REASONS",
                source_id,
                reason_counts["authority"],
            )

        if reason_counts["commercial"] > 1:
            fail(
                "TOO_MANY_COMMERCIAL_REASONS",
                source_id,
                reason_counts["commercial"],
            )

        normalized[source_id] = targets

    return normalized


def validate_graph(
    targets_by_source: dict[str, list[str]],
    article_ids: set[str],
) -> tuple[int, int, int]:
    incoming = Counter({article_id: 0 for article_id in article_ids})
    outgoing = Counter({article_id: 0 for article_id in article_ids})
    article_edge_count = 0

    for source_id, targets in targets_by_source.items():
        for target_id in targets:
            if target_id not in article_ids:
                continue

            outgoing[source_id] += 1
            incoming[target_id] += 1
            article_edge_count += 1

    low_outgoing = {
        article_id: outgoing[article_id]
        for article_id in sorted(article_ids)
        if outgoing[article_id] < MIN_ARTICLE_OUTGOING
    }
    if low_outgoing:
        fail("MIN_OUTGOING_ARTICLE_LINKS_FAILED", low_outgoing)

    low_incoming = {
        article_id: incoming[article_id]
        for article_id in sorted(article_ids)
        if incoming[article_id] < MIN_ARTICLE_INCOMING
    }
    if low_incoming:
        fail("MIN_INCOMING_ARTICLE_LINKS_FAILED", low_incoming)

    return (
        article_edge_count,
        min(incoming.values()),
        min(outgoing.values()),
    )


def run(args: argparse.Namespace) -> None:
    link_map = load_json(args.map, "LINK_MAP")
    topics_by_id = load_registry(args.registry)
    article_ids = load_article_ids(args.articles_dir)

    schema_version, links = validate_top_level(
        link_map,
        args.allow_v1_target_lists,
    )
    validate_source_set(links, article_ids)

    if schema_version == TRANSITIONAL_SCHEMA_VERSION:
        targets_by_source = validate_v1_links(
            links,
            topics_by_id,
        )
        map_format = "transitional_v1_target_lists"
    else:
        targets_by_source = validate_canonical_relationships(
            links,
            topics_by_id,
        )
        map_format = "canonical_v2_relationship_objects"

    (
        article_edge_count,
        min_incoming,
        min_outgoing,
    ) = validate_graph(targets_by_source, article_ids)

    print(f"SCHEMA_VERSION={schema_version}")
    print(f"MAP_FORMAT={map_format}")
    print(f"ARTICLE_COUNT={len(article_ids)}")
    print(f"MAP_SOURCE_COUNT={len(links)}")
    print(f"ARTICLE_EDGE_COUNT={article_edge_count}")
    print(f"MIN_INCOMING={min_incoming}")
    print(f"MIN_OUTGOING={min_outgoing}")

    if schema_version == TRANSITIONAL_SCHEMA_VERSION:
        print("INTERNAL_LINK_MAP_TRANSITIONAL_V1_OK")

    print("INTERNAL_LINK_MAP_VALIDATION_OK")


def main() -> int:
    args = parse_args()

    try:
        run(args)
    except ValidationError as exc:
        print(f"VALIDATION_ERROR={exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
