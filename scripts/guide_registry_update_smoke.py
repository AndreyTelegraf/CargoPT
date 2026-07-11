import copy
import json

from scripts.guide_registry_update import (
    registry_with_published_guide,
)
from scripts.guide_registry_update import serialize_registry


ARTICLE_ID = "test-guide"


def registry_with_status(status: str) -> dict:
    return {
        "version": 1,
        "locale": "pt-PT",
        "base_url": "https://cargopt.pt",
        "guides_hub": "/guias/",
        "statuses": [
            "planned",
            "draft",
            "published",
            "existing_landing",
        ],
        "topics": [
            {
                "id": ARTICLE_ID,
                "cluster": "prices",
                "title": "Test guide",
                "slug": "test-guide",
                "path": "/guias/precos/test-guide/",
                "primary_query": "test guide",
                "intent": ["informational"],
                "priority": 1,
                "status": status,
                "parent": "/guias/",
                "related": [],
            }
        ],
    }


def topic_for(registry: dict) -> dict:
    matches = [
        topic
        for topic in registry["topics"]
        if topic["id"] == ARTICLE_ID
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"expected one topic, got {len(matches)}"
        )

    return matches[0]


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
    source = registry_with_status(status)
    original = copy.deepcopy(source)

    updated = registry_with_published_guide(
        source,
        article_id=ARTICLE_ID,
    )

    if source != original:
        raise AssertionError("source registry was mutated")

    if updated is source:
        raise AssertionError("registry object was reused")

    updated_topic = topic_for(updated)

    if updated_topic["status"] != "published":
        raise AssertionError(
            f"unexpected updated status: "
            f"{updated_topic['status']}"
        )

    if topic_for(source)["status"] != status:
        raise AssertionError("source topic status changed")

    serialized = serialize_registry(updated)

    if not serialized.endswith("\n"):
        raise AssertionError("serialized registry lacks newline")

    if "\r\n" in serialized:
        raise AssertionError("serialized registry contains CRLF")

    parsed = json.loads(serialized)

    if topic_for(parsed)["status"] != "published":
        raise AssertionError(
            "serialized registry status is not published"
        )


def exercise_published_failure() -> None:
    registry = registry_with_status("published")

    require_failure(
        lambda: registry_with_published_guide(
            registry,
            article_id=ARTICLE_ID,
        ),
        "requires planned or draft status",
    )


def exercise_existing_landing_failure() -> None:
    registry = registry_with_status("existing_landing")

    require_failure(
        lambda: registry_with_published_guide(
            registry,
            article_id=ARTICLE_ID,
        ),
        "requires planned or draft status",
    )


def exercise_unknown_status_failure() -> None:
    registry = registry_with_status("unknown")

    require_failure(
        lambda: registry_with_published_guide(
            registry,
            article_id=ARTICLE_ID,
        ),
        "requires planned or draft status",
    )


def exercise_missing_topic_failure() -> None:
    registry = registry_with_status("planned")
    registry["topics"] = []

    require_failure(
        lambda: registry_with_published_guide(
            registry,
            article_id=ARTICLE_ID,
        ),
        "Expected exactly one registry topic",
    )


def exercise_duplicate_topic_failure() -> None:
    registry = registry_with_status("planned")
    registry["topics"].append(
        copy.deepcopy(registry["topics"][0])
    )

    require_failure(
        lambda: registry_with_published_guide(
            registry,
            article_id=ARTICLE_ID,
        ),
        "Expected exactly one registry topic",
    )


def main() -> None:
    exercise_success("planned")
    exercise_success("draft")
    exercise_published_failure()
    exercise_existing_landing_failure()
    exercise_unknown_status_failure()
    exercise_missing_topic_failure()
    exercise_duplicate_topic_failure()

    print("GUIDE_REGISTRY_UPDATE_SMOKE_OK")


if __name__ == "__main__":
    main()
