import copy
import json
from typing import Any

from scripts.guide_publish_preflight import find_topic


PUBLISHABLE_STATUSES = {"planned", "draft"}


def serialize_registry(registry: dict[str, Any]) -> str:
    return (
        json.dumps(
            registry,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def registry_with_published_guide(
    registry: dict[str, Any],
    *,
    article_id: str,
) -> dict[str, Any]:
    updated = copy.deepcopy(registry)
    topic = find_topic(updated, article_id)
    status = topic["status"]

    if status not in PUBLISHABLE_STATUSES:
        raise ValueError(
            "Guide publication requires planned or draft status, "
            f"got {status!r}: {article_id}"
        )

    topic["status"] = "published"
    return updated
