import argparse
import json
import sys
from collections import Counter
from collections import defaultdict
from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from scripts.guide_locale_contract import (
    validate_guide_locale_path,
)
from scripts.guide_translation_contract import (
    validate_guide_translation_contract,
)


DEFAULT_MAP = PROJECT_ROOT / "content/guides/internal-link-map.json"
DEFAULT_REGISTRY = PROJECT_ROOT / "content/guides/topics.json"
DEFAULT_ARTICLES_DIR = PROJECT_ROOT / "content/guides/articles"
DEFAULT_TEXT_REPORT = Path("/tmp/cargopt-corpus-release-audit.txt")
DEFAULT_JSON_REPORT = Path("/tmp/cargopt-corpus-release-audit.json")

OPTIONAL_ARTICLE_FIELDS = {
    "translation_group",
    "alternates",
    "content_mode",
}

REQUIRED_ARTICLE_FIELDS = {
    "schema_version",
    "id",
    "locale",
    "cluster",
    "path",
    "title",
    "meta_title",
    "meta_description",
    "primary_query",
    "intent",
    "article_section",
    "eyebrow",
    "hero_description",
    "date_published",
    "date_modified",
    "review_owner",
    "direct_answer_heading",
    "key_points_heading",
    "faq_heading",
    "related_links_heading",
    "direct_answer",
    "key_points",
    "sections",
    "mid_cta",
    "faq",
    "related_links",
    "final_cta",
}

ARTICLE_REGISTRY_FIELDS = (
    "id",
    "cluster",
    "path",
    "title",
    "primary_query",
    "intent",
)

ALLOWED_SECTION_FIELDS = {
    "id",
    "heading",
    "paragraphs",
    "items",
    "checklist",
    "blocks",
}

ALLOWED_LINK_TYPES = {
    "guide",
    "planned",
    "landing",
    "service",
    "parent",
}

ALLOWED_RELATIONSHIP_REASONS = {
    "same_cluster",
    "next_step",
    "dependency",
    "authority",
    "commercial",
    "conversion",
    "prerequisite",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    subject: str
    message: str


class Audit:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def add(
        self,
        severity: str,
        code: str,
        subject: str,
        message: str,
    ) -> None:
        self.findings.append(
            Finding(
                severity=severity,
                code=code,
                subject=subject,
                message=message,
            )
        )

    def error(
        self,
        code: str,
        subject: str,
        message: str,
    ) -> None:
        self.add("error", code, subject, message)

    def warning(
        self,
        code: str,
        subject: str,
        message: str,
    ) -> None:
        self.add("warning", code, subject, message)

    def info(
        self,
        code: str,
        subject: str,
        message: str,
    ) -> None:
        self.add("info", code, subject, message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a read-only release audit over the CargoPT "
            "structured guide corpus."
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
        "--text-report",
        type=Path,
        default=DEFAULT_TEXT_REPORT,
    )
    parser.add_argument(
        "--json-report",
        type=Path,
        default=DEFAULT_JSON_REPORT,
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in {path}: "
            f"line={error.lineno} column={error.colno}: {error.msg}"
        ) from error


def duplicate_values(
    values: list[str],
) -> dict[str, int]:
    return {
        value: count
        for value, count in Counter(values).items()
        if count > 1
    }


def require_nonempty_string(
    audit: Audit,
    *,
    article_id: str,
    field: str,
    value: Any,
) -> None:
    if not isinstance(value, str) or not value.strip():
        audit.error(
            "INVALID_STRING",
            article_id,
            f"{field} must be a non-empty string",
        )


def validate_cta(
    audit: Audit,
    article_id: str,
    name: str,
    value: Any,
) -> None:
    expected = {"heading", "text", "label", "href"}

    if not isinstance(value, dict):
        audit.error(
            "INVALID_CTA_TYPE",
            article_id,
            f"{name} must be an object",
        )
        return

    if set(value) != expected:
        audit.error(
            "INVALID_CTA_FIELDS",
            article_id,
            f"{name} fields={sorted(value)} expected={sorted(expected)}",
        )

    for field in expected:
        require_nonempty_string(
            audit,
            article_id=article_id,
            field=f"{name}.{field}",
            value=value.get(field),
        )


def validate_translation_groups(
    audit: Audit,
    articles: list[tuple[Path, dict[str, Any]]],
) -> None:
    translated_articles = [
        (path, article)
        for path, article in articles
        if (
            "translation_group" in article
            or "alternates" in article
        )
    ]

    if not translated_articles:
        return

    articles_by_path: dict[
        str,
        list[tuple[Path, dict[str, Any]]],
    ] = {}

    for path, article in translated_articles:
        article_path = article.get("path")

        if isinstance(article_path, str):
            articles_by_path.setdefault(
                article_path,
                [],
            ).append((path, article))

    groups: dict[
        str,
        list[tuple[Path, dict[str, Any]]],
    ] = {}

    for path, article in translated_articles:
        group = article.get("translation_group")

        if isinstance(group, str) and group.strip():
            groups.setdefault(group, []).append(
                (path, article)
            )

    for group, members in groups.items():
        locales: dict[
            str,
            list[tuple[Path, dict[str, Any]]],
        ] = {}

        canonical_alternates: dict[str, str] | None = None

        for path, article in members:
            locale = article.get("locale")

            if isinstance(locale, str):
                locales.setdefault(locale, []).append(
                    (path, article)
                )

            alternates = article.get("alternates")

            if not isinstance(alternates, dict):
                continue

            if canonical_alternates is None:
                canonical_alternates = alternates
            elif alternates != canonical_alternates:
                audit.error(
                    "TRANSLATION_ALTERNATES_MISMATCH",
                    group,
                    (
                        f"article={article.get('id')!r} "
                        f"file={path}"
                    ),
                )

        for locale, locale_members in locales.items():
            if len(locale_members) <= 1:
                continue

            article_ids = sorted(
                str(member.get("id"))
                for _, member in locale_members
            )

            audit.error(
                "DUPLICATE_TRANSLATION_LOCALE",
                group,
                (
                    f"locale={locale!r} "
                    f"articles={article_ids}"
                ),
            )

        if canonical_alternates is None:
            continue

        for alternate_locale, alternate_path in (
            canonical_alternates.items()
        ):
            targets = articles_by_path.get(
                alternate_path,
                [],
            )

            if not targets:
                audit.error(
                    "MISSING_TRANSLATION_TARGET",
                    group,
                    (
                        f"locale={alternate_locale!r} "
                        f"path={alternate_path!r}"
                    ),
                )
                continue

            if len(targets) > 1:
                audit.error(
                    "AMBIGUOUS_TRANSLATION_TARGET",
                    group,
                    (
                        f"locale={alternate_locale!r} "
                        f"path={alternate_path!r} "
                        f"matches={len(targets)}"
                    ),
                )
                continue

            _, target = targets[0]

            target_group = target.get("translation_group")

            if target_group != group:
                audit.error(
                    "TRANSLATION_TARGET_GROUP_MISMATCH",
                    group,
                    (
                        f"locale={alternate_locale!r} "
                        f"path={alternate_path!r} "
                        f"target_group={target_group!r}"
                    ),
                )

            target_locale = target.get("locale")

            if target_locale != alternate_locale:
                audit.error(
                    "TRANSLATION_TARGET_LOCALE_MISMATCH",
                    group,
                    (
                        f"path={alternate_path!r} "
                        f"expected_locale={alternate_locale!r} "
                        f"actual_locale={target_locale!r}"
                    ),
                )


def validate_article_structure(
    audit: Audit,
    *,
    path: Path,
    article: dict[str, Any],
) -> None:
    article_id = str(article.get("id") or path.stem)

    missing = sorted(REQUIRED_ARTICLE_FIELDS - set(article))
    allowed_fields = (
        REQUIRED_ARTICLE_FIELDS
        | OPTIONAL_ARTICLE_FIELDS
    )
    extra = sorted(set(article) - allowed_fields)

    if missing:
        audit.error(
            "MISSING_ARTICLE_FIELDS",
            article_id,
            f"missing={missing}",
        )

    if extra:
        audit.error(
            "EXTRA_ARTICLE_FIELDS",
            article_id,
            f"extra={extra}",
        )

    if article.get("schema_version") != 1:
        audit.error(
            "INVALID_SCHEMA_VERSION",
            article_id,
            f"value={article.get('schema_version')!r}",
        )

    locale = article.get("locale")
    path_value = article.get("path")

    if isinstance(locale, str) and isinstance(path_value, str):
        try:
            validate_guide_locale_path(
                locale=locale,
                path=path_value,
            )
        except ValueError as error:
            code = str(error).split(":", 1)[0]
            audit.error(
                code,
                article_id,
                str(error),
            )

    try:
        validate_guide_translation_contract(article)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, ValueError):
            code = str(error).split(":", 1)[0]
        else:
            code = "INVALID_TRANSLATION_METADATA"

        audit.error(
            code,
            article_id,
            str(error),
        )

    content_mode = article.get("content_mode")

    if content_mode not in {None, "verbatim"}:
        audit.error(
            "INVALID_CONTENT_MODE",
            article_id,
            f"value={content_mode!r}",
        )

    if article.get("review_owner") != "CargoPT":
        audit.error(
            "INVALID_REVIEW_OWNER",
            article_id,
            f"value={article.get('review_owner')!r}",
        )

    for field in (
        "id",
        "cluster",
        "path",
        "title",
        "meta_title",
        "meta_description",
        "primary_query",
        "article_section",
        "eyebrow",
        "hero_description",
        "direct_answer_heading",
        "key_points_heading",
        "faq_heading",
        "related_links_heading",
        "direct_answer",
    ):
        require_nonempty_string(
            audit,
            article_id=article_id,
            field=field,
            value=article.get(field),
        )

    intent = article.get("intent")

    if not isinstance(intent, list) or not intent:
        audit.error(
            "INVALID_INTENT",
            article_id,
            "intent must be a non-empty list",
        )

    key_points = article.get("key_points")

    if not isinstance(key_points, list):
        audit.error(
            "INVALID_KEY_POINTS_TYPE",
            article_id,
            "key_points must be a list",
        )
    else:
        if not 3 <= len(key_points) <= 6:
            audit.error(
                "INVALID_KEY_POINTS_COUNT",
                article_id,
                f"count={len(key_points)}",
            )

        for index, item in enumerate(key_points, start=1):
            require_nonempty_string(
                audit,
                article_id=article_id,
                field=f"key_points[{index}]",
                value=item,
            )

    sections = article.get("sections")

    if not isinstance(sections, list):
        audit.error(
            "INVALID_SECTIONS_TYPE",
            article_id,
            "sections must be a list",
        )
    else:
        if len(sections) < 5:
            audit.error(
                "TOO_FEW_SECTIONS",
                article_id,
                f"count={len(sections)}",
            )

        section_ids: list[str] = []

        for index, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                audit.error(
                    "INVALID_SECTION_TYPE",
                    article_id,
                    f"section[{index}] must be an object",
                )
                continue

            unknown = sorted(set(section) - ALLOWED_SECTION_FIELDS)

            if unknown:
                audit.error(
                    "INVALID_SECTION_FIELDS",
                    article_id,
                    f"section[{index}] extra={unknown}",
                )

            section_id = section.get("id")

            require_nonempty_string(
                audit,
                article_id=article_id,
                field=f"sections[{index}].id",
                value=section_id,
            )
            require_nonempty_string(
                audit,
                article_id=article_id,
                field=f"sections[{index}].heading",
                value=section.get("heading"),
            )

            if isinstance(section_id, str):
                section_ids.append(section_id)

            content_fields = {
                field
                for field in (
                    "paragraphs",
                    "items",
                    "checklist",
                    "blocks",
                )
                if section.get(field)
            }

            if not content_fields:
                audit.error(
                    "EMPTY_SECTION_CONTENT",
                    article_id,
                    f"section[{index}] has no content",
                )

            blocks = section.get("blocks")

            if blocks is not None:
                if not isinstance(blocks, list) or not blocks:
                    audit.error(
                        "INVALID_ORDERED_BLOCKS",
                        article_id,
                        f"section[{index}]",
                    )
                else:
                    for block_index, block in enumerate(
                        blocks,
                        start=1,
                    ):
                        subject = (
                            f"sections[{index}]."
                            f"blocks[{block_index}]"
                        )

                        if not isinstance(block, dict):
                            audit.error(
                                "INVALID_ORDERED_BLOCK",
                                article_id,
                                subject,
                            )
                            continue

                        block_type = block.get("type")

                        if block_type in {
                            "paragraph",
                            "subheading",
                        }:
                            if set(block) != {"type", "text"}:
                                audit.error(
                                    "INVALID_ORDERED_BLOCK_FIELDS",
                                    article_id,
                                    subject,
                                )
                            require_nonempty_string(
                                audit,
                                article_id=article_id,
                                field=f"{subject}.text",
                                value=block.get("text"),
                            )
                        elif block_type == "checklist":
                            if set(block) != {"type", "items"}:
                                audit.error(
                                    "INVALID_ORDERED_BLOCK_FIELDS",
                                    article_id,
                                    subject,
                                )

                            items = block.get("items")

                            if (
                                not isinstance(items, list)
                                or not items
                            ):
                                audit.error(
                                    "INVALID_ORDERED_CHECKLIST",
                                    article_id,
                                    subject,
                                )
                            else:
                                for item_index, item in enumerate(
                                    items,
                                    start=1,
                                ):
                                    require_nonempty_string(
                                        audit,
                                        article_id=article_id,
                                        field=(
                                            f"{subject}.items"
                                            f"[{item_index}]"
                                        ),
                                        value=item,
                                    )
                        else:
                            audit.error(
                                "INVALID_ORDERED_BLOCK_TYPE",
                                article_id,
                                f"{subject}:{block_type!r}",
                            )

            paragraphs = section.get("paragraphs")

            if paragraphs is not None:
                if not isinstance(paragraphs, list) or not paragraphs:
                    audit.error(
                        "INVALID_PARAGRAPHS",
                        article_id,
                        f"section[{index}]",
                    )
                else:
                    for paragraph_index, paragraph in enumerate(
                        paragraphs,
                        start=1,
                    ):
                        require_nonempty_string(
                            audit,
                            article_id=article_id,
                            field=(
                                f"sections[{index}]."
                                f"paragraphs[{paragraph_index}]"
                            ),
                            value=paragraph,
                        )

        duplicates = duplicate_values(section_ids)

        if duplicates:
            audit.error(
                "DUPLICATE_SECTION_IDS",
                article_id,
                f"duplicates={duplicates}",
            )

    faq = article.get("faq")

    if not isinstance(faq, list):
        audit.error(
            "INVALID_FAQ_TYPE",
            article_id,
            "faq must be a list",
        )
    else:
        if not 3 <= len(faq) <= 6:
            audit.error(
                "INVALID_FAQ_COUNT",
                article_id,
                f"count={len(faq)}",
            )

        questions: list[str] = []

        for index, item in enumerate(faq, start=1):
            if not isinstance(item, dict):
                audit.error(
                    "INVALID_FAQ_ITEM",
                    article_id,
                    f"faq[{index}] must be an object",
                )
                continue

            if set(item) != {"question", "answer"}:
                audit.error(
                    "INVALID_FAQ_FIELDS",
                    article_id,
                    f"faq[{index}] fields={sorted(item)}",
                )

            question = item.get("question")

            require_nonempty_string(
                audit,
                article_id=article_id,
                field=f"faq[{index}].question",
                value=question,
            )
            require_nonempty_string(
                audit,
                article_id=article_id,
                field=f"faq[{index}].answer",
                value=item.get("answer"),
            )

            if isinstance(question, str):
                questions.append(question)

                if not question.endswith("?"):
                    audit.warning(
                        "FAQ_WITHOUT_QUESTION_MARK",
                        article_id,
                        f"question={question!r}",
                    )

        duplicates = duplicate_values(questions)

        if duplicates:
            audit.error(
                "DUPLICATE_FAQ_QUESTIONS",
                article_id,
                f"duplicates={duplicates}",
            )

    related_links = article.get("related_links")

    if not isinstance(related_links, list):
        audit.error(
            "INVALID_RELATED_LINKS_TYPE",
            article_id,
            "related_links must be a list",
        )
    else:
        if not related_links:
            audit.error(
                "EMPTY_RELATED_LINKS",
                article_id,
                "related_links is empty",
            )

        for index, item in enumerate(related_links, start=1):
            if not isinstance(item, dict):
                audit.error(
                    "INVALID_RELATED_LINK",
                    article_id,
                    f"related_links[{index}] must be an object",
                )
                continue

            if set(item) != {"title", "href", "type"}:
                audit.error(
                    "INVALID_RELATED_LINK_FIELDS",
                    article_id,
                    f"related_links[{index}] fields={sorted(item)}",
                )

            for field in ("title", "href", "type"):
                require_nonempty_string(
                    audit,
                    article_id=article_id,
                    field=f"related_links[{index}].{field}",
                    value=item.get(field),
                )

            link_type = item.get("type")

            if (
                isinstance(link_type, str)
                and link_type not in ALLOWED_LINK_TYPES
            ):
                audit.error(
                    "UNKNOWN_RELATED_LINK_TYPE",
                    article_id,
                    f"type={link_type!r}",
                )

    validate_cta(
        audit,
        article_id,
        "mid_cta",
        article.get("mid_cta"),
    )
    validate_cta(
        audit,
        article_id,
        "final_cta",
        article.get("final_cta"),
    )



def build_graph_audit(
    audit: Audit,
    topics: list[dict[str, Any]],
    articles: list[tuple[Path, dict[str, Any]]],
) -> dict[str, Any]:
    topics_by_path = {
        topic["path"]: topic
        for topic in topics
        if isinstance(topic.get("path"), str)
    }
    article_ids = {
        article["id"]
        for _, article in articles
        if isinstance(article.get("id"), str)
    }
    incoming = Counter({article_id: 0 for article_id in article_ids})
    outgoing = Counter({article_id: 0 for article_id in article_ids})
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    edges = []
    registry_only = []
    static_edges = []
    broken = []
    self_links = []
    duplicates = []

    for _, article in articles:
        source_id = article["id"]
        source_cluster = article["cluster"]
        href_counts = Counter()

        for link in article.get("related_links", []):
            href = link.get("href")
            if not isinstance(href, str):
                continue

            href_counts[href] += 1

            if href == "/#request":
                continue

            target = topics_by_path.get(href)

            if target is None:
                static_path = (
                    PROJECT_ROOT
                    / "app/static"
                    / href.strip("/")
                    / "index.html"
                )

                if href.startswith("/") and static_path.is_file():
                    static_edges.append(
                        {
                            "source": source_id,
                            "href": href,
                            "path": str(
                                static_path.relative_to(PROJECT_ROOT)
                            ),
                        }
                    )
                    continue

                if href.startswith("/"):
                    broken.append({"source": source_id, "href": href})
                    audit.error(
                        "BROKEN_INTERNAL_RELATED_LINK",
                        source_id,
                        f"href={href!r}",
                    )
                continue

            target_id = target["id"]

            if target_id == source_id:
                self_links.append({"source": source_id, "href": href})
                audit.error(
                    "SELF_RELATED_LINK",
                    source_id,
                    f"href={href!r}",
                )
            elif target_id in article_ids:
                incoming[target_id] += 1
                outgoing[source_id] += 1
                matrix[source_cluster][target["cluster"]] += 1
                edges.append(
                    {"source": source_id, "target": target_id}
                )
            else:
                registry_only.append(
                    {
                        "source": source_id,
                        "target": target_id,
                        "status": target.get("status"),
                    }
                )

        for href, count in href_counts.items():
            if count > 1:
                duplicates.append(
                    {"source": source_id, "href": href, "count": count}
                )
                audit.warning(
                    "DUPLICATE_OUTGOING_RELATED_LINK",
                    source_id,
                    f"href={href!r} count={count}",
                )

    orphans = sorted(
        article_id
        for article_id, count in incoming.items()
        if count == 0
    )

    for article_id in orphans:
        audit.warning(
            "ORPHAN_ARTICLE",
            article_id,
            "no incoming related links",
        )

    node_count = len(article_ids)
    edge_count = len(edges)

    dead_ends = sorted(
        article_id
        for article_id, count in outgoing.items()
        if count == 0
    )
    low_incoming = sorted(
        article_id
        for article_id, count in incoming.items()
        if count <= 1
    )
    low_outgoing = sorted(
        article_id
        for article_id, count in outgoing.items()
        if count < 2
    )

    top_incoming = [
        {
            "article_id": article_id,
            "count": count,
        }
        for article_id, count in sorted(
            incoming.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]
    top_outgoing = [
        {
            "article_id": article_id,
            "count": count,
        }
        for article_id, count in sorted(
            outgoing.items(),
            key=lambda item: (-item[1], item[0]),
        )[:10]
    ]

    top_two_incoming = sum(
        item["count"]
        for item in top_incoming[:2]
    )

    seo_efficiency = {
        "average_incoming": (
            round(edge_count / node_count, 2)
            if node_count
            else 0.0
        ),
        "average_outgoing": (
            round(edge_count / node_count, 2)
            if node_count
            else 0.0
        ),
        "orphan_ratio_percent": (
            round(len(orphans) * 100 / node_count, 1)
            if node_count
            else 0.0
        ),
        "dead_end_ratio_percent": (
            round(len(dead_ends) * 100 / node_count, 1)
            if node_count
            else 0.0
        ),
        "top_two_incoming_share_percent": (
            round(top_two_incoming * 100 / edge_count, 1)
            if edge_count
            else 0.0
        ),
        "dead_end_articles": dead_ends,
        "low_incoming_articles": low_incoming,
        "low_outgoing_articles": low_outgoing,
        "top_incoming": top_incoming,
        "top_outgoing": top_outgoing,
    }

    return {
        "summary": {
            "nodes": len(article_ids),
            "edges": len(edges),
            "registry_only_edges": len(registry_only),
            "static_edges": len(static_edges),
            "broken": len(broken),
            "self_links": len(self_links),
            "duplicates": len(duplicates),
            "orphans": len(orphans),
        },
        "incoming": dict(sorted(incoming.items())),
        "outgoing": dict(sorted(outgoing.items())),
        "orphans": orphans,
        "cluster_matrix": {
            source: dict(sorted(targets.items()))
            for source, targets in sorted(matrix.items())
        },
        "edges": edges,
        "registry_only": registry_only,
        "static_edges": static_edges,
        "broken": broken,
        "self_links": self_links,
        "duplicates": duplicates,
        "seo_efficiency": seo_efficiency,
    }


def build_canonical_map_audit(
    audit: Audit,
    *,
    map_path: Path,
    topics: list[dict[str, Any]],
    articles_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    try:
        link_map = load_json(map_path)
    except (OSError, ValueError) as error:
        audit.error(
            "INVALID_CANONICAL_MAP",
            "internal-link-map",
            str(error),
        )
        return {
            "schema_version": None,
            "source_count": 0,
            "relationship_count": 0,
            "reason_counts": {},
            "article_edges": 0,
            "registry_only_edges": 0,
            "conversion_edges": 0,
            "render_mismatches": [],
        }

    if not isinstance(link_map, dict):
        audit.error(
            "INVALID_CANONICAL_MAP_TYPE",
            "internal-link-map",
            "map root must be an object",
        )
        return {
            "schema_version": None,
            "source_count": 0,
            "relationship_count": 0,
            "reason_counts": {},
            "article_edges": 0,
            "registry_only_edges": 0,
            "conversion_edges": 0,
            "render_mismatches": [],
        }

    schema_version = link_map.get("schema_version")
    links = link_map.get("links")
    request_target = link_map.get("request_target")

    if schema_version != 2:
        audit.error(
            "INVALID_CANONICAL_MAP_SCHEMA",
            "internal-link-map",
            f"schema_version={schema_version!r}",
        )

    if not isinstance(links, dict):
        audit.error(
            "INVALID_CANONICAL_MAP_LINKS",
            "internal-link-map",
            "links must be an object",
        )
        links = {}

    if not isinstance(request_target, dict):
        audit.error(
            "INVALID_CANONICAL_REQUEST_TARGET",
            "internal-link-map",
            "request_target must be an object",
        )
        request_target = {}

    article_ids = set(articles_by_id)
    map_source_ids = set(links)

    if map_source_ids != article_ids:
        audit.error(
            "CANONICAL_MAP_ARTICLE_SET_MISMATCH",
            "internal-link-map",
            (
                f"missing={sorted(article_ids - map_source_ids)}:"
                f"extra={sorted(map_source_ids - article_ids)}"
            ),
        )

    topics_by_id = {
        topic["id"]: topic
        for topic in topics
        if isinstance(topic, dict)
        and isinstance(topic.get("id"), str)
    }

    request_id = request_target.get("id")
    request_href = request_target.get("href")

    reason_counts: Counter[str] = Counter()
    article_edges = 0
    registry_only_edges = 0
    conversion_edges = 0
    relationship_count = 0
    render_mismatches: list[dict[str, Any]] = []

    for source_id, relationships in sorted(links.items()):
        if not isinstance(relationships, list):
            audit.error(
                "INVALID_CANONICAL_RELATIONSHIP_LIST",
                source_id,
                f"value={relationships!r}",
            )
            continue

        ordered: list[tuple[int, str, str]] = []

        for relationship in relationships:
            relationship_count += 1

            if not isinstance(relationship, dict):
                audit.error(
                    "INVALID_CANONICAL_RELATIONSHIP",
                    source_id,
                    f"value={relationship!r}",
                )
                continue

            if set(relationship) != {
                "target",
                "reason",
                "priority",
            }:
                audit.error(
                    "INVALID_CANONICAL_RELATIONSHIP_FIELDS",
                    source_id,
                    f"fields={sorted(relationship)}",
                )

            target_id = relationship.get("target")
            reason = relationship.get("reason")
            priority = relationship.get("priority")

            if not isinstance(target_id, str) or not target_id:
                audit.error(
                    "INVALID_CANONICAL_TARGET",
                    source_id,
                    f"value={target_id!r}",
                )
                continue

            if (
                not isinstance(priority, int)
                or isinstance(priority, bool)
            ):
                audit.error(
                    "INVALID_CANONICAL_PRIORITY",
                    source_id,
                    f"value={priority!r}",
                )
                continue

            if (
                not isinstance(reason, str)
                or reason not in ALLOWED_RELATIONSHIP_REASONS
            ):
                audit.error(
                    "INVALID_CANONICAL_REASON",
                    source_id,
                    f"value={reason!r}",
                )
                continue

            reason_counts[reason] += 1
            ordered.append((priority, target_id, reason))

            if target_id == request_id:
                conversion_edges += 1
            elif target_id in article_ids:
                article_edges += 1
            elif target_id in topics_by_id:
                registry_only_edges += 1
            else:
                audit.error(
                    "UNKNOWN_CANONICAL_TARGET",
                    source_id,
                    f"target={target_id!r}",
                )

        ordered.sort(key=lambda item: item[0])

        priorities = [
            priority
            for priority, _, _ in ordered
        ]

        if priorities != [1, 2, 3, 4]:
            audit.error(
                "INVALID_CANONICAL_PRIORITY_SEQUENCE",
                source_id,
                f"priorities={priorities}",
            )

        expected_hrefs: list[str] = []

        for _, target_id, _ in ordered:
            if target_id == request_id:
                expected_hrefs.append(str(request_href))
                continue

            topic = topics_by_id.get(target_id)

            if topic is None:
                continue

            expected_hrefs.append(str(topic.get("path")))

        article_entry = articles_by_id.get(source_id)

        if article_entry is None:
            continue

        _, article = article_entry

        actual_hrefs = [
            link.get("href")
            for link in article.get("related_links", [])
            if isinstance(link, dict)
        ]

        if actual_hrefs != expected_hrefs:
            mismatch = {
                "source": source_id,
                "expected": expected_hrefs,
                "actual": actual_hrefs,
            }
            render_mismatches.append(mismatch)
            audit.error(
                "CANONICAL_MAP_RENDER_MISMATCH",
                source_id,
                (
                    f"expected={expected_hrefs}:"
                    f"actual={actual_hrefs}"
                ),
            )

    return {
        "schema_version": schema_version,
        "source_count": len(links),
        "relationship_count": relationship_count,
        "reason_counts": dict(sorted(reason_counts.items())),
        "article_edges": article_edges,
        "registry_only_edges": registry_only_edges,
        "conversion_edges": conversion_edges,
        "render_mismatches": render_mismatches,
    }


def main() -> None:
    args = parse_args()
    audit = Audit()

    if not args.registry.is_file():
        raise FileNotFoundError(args.registry)

    if not args.articles_dir.is_dir():
        raise NotADirectoryError(args.articles_dir)

    registry = load_json(args.registry)

    if not isinstance(registry, dict):
        raise ValueError("Registry root must be an object")

    topics = registry.get("topics")

    if not isinstance(topics, list):
        raise ValueError("Registry topics must be a list")

    article_paths = sorted(args.articles_dir.glob("*.json"))
    articles: list[tuple[Path, dict[str, Any]]] = []

    for path in article_paths:
        value = load_json(path)

        if not isinstance(value, dict):
            audit.error(
                "INVALID_ARTICLE_ROOT",
                path.name,
                "article root must be an object",
            )
            continue

        articles.append((path, value))
        validate_article_structure(
            audit,
            path=path,
            article=value,
        )

    validate_translation_groups(
        audit,
        articles,
    )

    topic_ids = [
        str(topic.get("id"))
        for topic in topics
        if topic.get("id") is not None
    ]
    topic_slugs = [
        str(topic.get("slug"))
        for topic in topics
        if topic.get("slug") is not None
    ]
    topic_paths = [
        str(topic.get("path"))
        for topic in topics
        if topic.get("path") is not None
    ]

    article_ids = [
        str(article.get("id"))
        for _, article in articles
        if article.get("id") is not None
    ]
    article_paths_values = [
        str(article.get("path"))
        for _, article in articles
        if article.get("path") is not None
    ]
    article_queries = [
        str(article.get("primary_query"))
        for _, article in articles
        if article.get("primary_query") is not None
    ]
    article_meta_titles = [
        str(article.get("meta_title"))
        for _, article in articles
        if article.get("meta_title") is not None
    ]
    article_meta_descriptions = [
        str(article.get("meta_description"))
        for _, article in articles
        if article.get("meta_description") is not None
    ]

    duplicate_sets = {
        "registry_id": duplicate_values(topic_ids),
        "registry_slug": duplicate_values(topic_slugs),
        "registry_path": duplicate_values(topic_paths),
        "article_id": duplicate_values(article_ids),
        "article_path": duplicate_values(article_paths_values),
        "article_primary_query": duplicate_values(article_queries),
        "article_meta_title": duplicate_values(article_meta_titles),
        "article_meta_description": duplicate_values(
            article_meta_descriptions
        ),
    }

    for name, duplicates in duplicate_sets.items():
        if duplicates:
            audit.error(
                "DUPLICATE_VALUES",
                name,
                json.dumps(
                    duplicates,
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            )

    topics_by_id = {
        topic["id"]: topic
        for topic in topics
        if isinstance(topic, dict) and isinstance(topic.get("id"), str)
    }

    articles_by_id = {
        article["id"]: (path, article)
        for path, article in articles
        if isinstance(article.get("id"), str)
    }

    for article_id, (path, article) in articles_by_id.items():
        topic = topics_by_id.get(article_id)

        if topic is None:
            audit.error(
                "ARTICLE_WITHOUT_REGISTRY_TOPIC",
                article_id,
                f"file={path}",
            )
            continue

        for field in ARTICLE_REGISTRY_FIELDS:
            if article.get(field) != topic.get(field):
                audit.error(
                    "ARTICLE_REGISTRY_MISMATCH",
                    article_id,
                    (
                        f"field={field} "
                        f"article={article.get(field)!r} "
                        f"registry={topic.get(field)!r}"
                    ),
                )

        slug = topic.get("slug")

        if path.stem != slug:
            audit.error(
                "ARTICLE_FILENAME_SLUG_MISMATCH",
                article_id,
                f"filename={path.stem!r} registry_slug={slug!r}",
            )

    graph = build_graph_audit(audit, topics, articles)

    planned_without_json = [
        topic["id"]
        for topic in topics
        if (
            topic.get("status") == "planned"
            and topic.get("id") not in articles_by_id
        )
    ]

    if planned_without_json:
        audit.error(
            "PLANNED_WITHOUT_JSON",
            "registry",
            f"ids={sorted(planned_without_json)}",
        )

    missing_topics = [
        topic
        for topic in topics
        if topic.get("id") not in articles_by_id
    ]

    unexpected_missing = [
        topic.get("id")
        for topic in missing_topics
        if topic.get("status") != "existing_landing"
    ]

    if unexpected_missing:
        audit.error(
            "NON_LANDING_TOPIC_WITHOUT_JSON",
            "registry",
            f"ids={sorted(unexpected_missing)}",
        )

    canonical_map = build_canonical_map_audit(
        audit,
        map_path=args.map,
        topics=topics,
        articles_by_id=articles_by_id,
    )

    status_counts = Counter(
        topic.get("status")
        for topic in topics
    )
    registry_cluster_counts = Counter(
        topic.get("cluster")
        for topic in topics
    )
    article_cluster_counts = Counter(
        article.get("cluster")
        for _, article in articles
    )
    link_type_counts = Counter(
        link.get("type")
        for _, article in articles
        for link in article.get("related_links", [])
        if isinstance(link, dict)
    )

    severity_counts = Counter(
        finding.severity
        for finding in audit.findings
    )

    report = {
        "summary": {
            "registry_topics": len(topics),
            "article_files": len(article_paths),
            "loaded_articles": len(articles),
            "coverage_percent": (
                round(len(articles) * 100 / len(topics), 1)
                if topics
                else 0.0
            ),
            "planned_without_json": len(planned_without_json),
            "missing_registry_topics": len(missing_topics),
            "finding_counts": dict(sorted(severity_counts.items())),
        },
        "registry_status_counts": dict(
            sorted(
                status_counts.items(),
                key=lambda item: str(item[0]),
            )
        ),
        "registry_cluster_counts": dict(
            sorted(
                registry_cluster_counts.items(),
                key=lambda item: str(item[0]),
            )
        ),
        "article_cluster_counts": dict(
            sorted(
                article_cluster_counts.items(),
                key=lambda item: str(item[0]),
            )
        ),
        "related_link_type_counts": dict(
            sorted(
                link_type_counts.items(),
                key=lambda item: str(item[0]),
            )
        ),
        "canonical_map": canonical_map,
        "graph": graph,
        "duplicate_sets": duplicate_sets,
        "findings": [
            asdict(finding)
            for finding in audit.findings
        ],
    }

    args.json_report.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = [
        "CargoPT Corpus Release Audit",
        "============================",
        "",
        f"Registry topics       : {len(topics)}",
        f"Article files         : {len(article_paths)}",
        f"Loaded articles       : {len(articles)}",
        (
            "Coverage              : "
            f"{len(articles)}/{len(topics)} "
            f"({report['summary']['coverage_percent']:.1f}%)"
        ),
        f"Planned without JSON  : {len(planned_without_json)}",
        f"Missing registry topics: {len(missing_topics)}",
        "",
        "Canonical map:",
        (
            "  schema version       : "
            f"{canonical_map['schema_version']}"
        ),
        (
            "  sources              : "
            f"{canonical_map['source_count']}"
        ),
        (
            "  relationships        : "
            f"{canonical_map['relationship_count']}"
        ),
        (
            "  article edges        : "
            f"{canonical_map['article_edges']}"
        ),
        (
            "  registry-only edges  : "
            f"{canonical_map['registry_only_edges']}"
        ),
        (
            "  conversion edges     : "
            f"{canonical_map['conversion_edges']}"
        ),
        (
            "  render mismatches    : "
            f"{len(canonical_map['render_mismatches'])}"
        ),
        (
            "  reasons              : "
            + ", ".join(
                f"{reason}={count}"
                for reason, count
                in canonical_map["reason_counts"].items()
            )
        ),
        "",
        "Findings:",
        f"  errors   : {severity_counts.get('error', 0)}",
        f"  warnings : {severity_counts.get('warning', 0)}",
        f"  info     : {severity_counts.get('info', 0)}",
        "",
        "Registry statuses:",
    ]

    for status, count in sorted(
        status_counts.items(),
        key=lambda item: str(item[0]),
    ):
        lines.append(f"  {status}: {count}")

    lines.extend(["", "Article clusters:"])

    for cluster, count in sorted(
        article_cluster_counts.items(),
        key=lambda item: str(item[0]),
    ):
        lines.append(f"  {cluster}: {count}")

    lines.extend(["", "Related link types:"])

    for link_type, count in sorted(
        link_type_counts.items(),
        key=lambda item: str(item[0]),
    ):
        lines.append(f"  {link_type}: {count}")

    graph_summary = graph["summary"]

    lines.extend(
        [
            "",
            "Graph:",
            f"  nodes               : {graph_summary['nodes']}",
            f"  article edges       : {graph_summary['edges']}",
            (
                "  registry-only edges : "
                f"{graph_summary['registry_only_edges']}"
            ),
            (
                "  static page edges   : "
                f"{graph_summary['static_edges']}"
            ),
            f"  broken links        : {graph_summary['broken']}",
            f"  self links          : {graph_summary['self_links']}",
            f"  duplicate links     : {graph_summary['duplicates']}",
            f"  orphan articles     : {graph_summary['orphans']}",
            "",
            "Incoming links by article:",
        ]
    )

    for article_id, count in sorted(
        graph["incoming"].items(),
        key=lambda item: (item[1], item[0]),
    ):
        lines.append(f"  {count:2d}  {article_id}")

    lines.extend(["", "Outgoing links by article:"])

    for article_id, count in sorted(
        graph["outgoing"].items(),
        key=lambda item: (item[1], item[0]),
    ):
        lines.append(f"  {count:2d}  {article_id}")

    lines.extend(["", "Cluster link matrix:"])

    for source_cluster, targets in graph[
        "cluster_matrix"
    ].items():
        rendered = ", ".join(
            f"{target}={count}"
            for target, count in targets.items()
        )
        lines.append(f"  {source_cluster}: {rendered}")

    if graph["orphans"]:
        lines.extend(["", "Orphan articles:"])

        for article_id in graph["orphans"]:
            lines.append(f"  {article_id}")

    seo = graph["seo_efficiency"]

    lines.extend(
        [
            "",
            "SEO graph efficiency:",
            (
                "  average incoming links       : "
                f"{seo['average_incoming']:.2f}"
            ),
            (
                "  average outgoing links       : "
                f"{seo['average_outgoing']:.2f}"
            ),
            (
                "  orphan ratio                 : "
                f"{seo['orphan_ratio_percent']:.1f}%"
            ),
            (
                "  dead-end ratio               : "
                f"{seo['dead_end_ratio_percent']:.1f}%"
            ),
            (
                "  top-two incoming share       : "
                f"{seo['top_two_incoming_share_percent']:.1f}%"
            ),
            (
                "  low incoming articles        : "
                f"{len(seo['low_incoming_articles'])}"
            ),
            (
                "  low outgoing articles        : "
                f"{len(seo['low_outgoing_articles'])}"
            ),
            (
                "  dead-end articles            : "
                f"{len(seo['dead_end_articles'])}"
            ),
            "",
            "Top articles by incoming links:",
        ]
    )

    for item in seo["top_incoming"]:
        lines.append(
            f"  {item['count']:2d}  {item['article_id']}"
        )

    lines.extend(["", "Top articles by outgoing links:"])

    for item in seo["top_outgoing"]:
        lines.append(
            f"  {item['count']:2d}  {item['article_id']}"
        )

    if seo["dead_end_articles"]:
        lines.extend(["", "Dead-end articles:"])

        for article_id in seo["dead_end_articles"]:
            lines.append(f"  {article_id}")

    if seo["low_incoming_articles"]:
        lines.extend(["", "Low incoming articles (0-1):"])

        for article_id in seo["low_incoming_articles"]:
            lines.append(f"  {article_id}")

    if seo["low_outgoing_articles"]:
        lines.extend(["", "Low outgoing articles (<2):"])

        for article_id in seo["low_outgoing_articles"]:
            lines.append(f"  {article_id}")

    if audit.findings:
        lines.extend(["", "Detailed findings:"])

        for finding in audit.findings:
            lines.append(
                f"  [{finding.severity.upper()}] "
                f"{finding.code} "
                f"{finding.subject}: "
                f"{finding.message}"
            )

    args.text_report.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("\n".join(lines))
    print()
    print(f"TEXT_REPORT={args.text_report}")
    print(f"JSON_REPORT={args.json_report}")

    error_count = severity_counts.get("error", 0)

    if error_count:
        print(f"CORPUS_RELEASE_INTEGRITY_FAILED errors={error_count}")
        raise SystemExit(1)

    print("CORPUS_RELEASE_INTEGRITY_OK")


if __name__ == "__main__":
    main()
