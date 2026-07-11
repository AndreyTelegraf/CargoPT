import json
from pathlib import Path


ALLOWED_STATUSES = {
    "planned",
    "draft",
    "published",
    "existing_landing",
}

ALLOWED_INTENTS = {
    "commercial",
    "transactional",
    "informational",
    "local",
}


def main() -> None:
    registry_path = Path("content/guides/topics.json")
    static_root = Path("app/static")

    assert registry_path.is_file()

    data = json.loads(registry_path.read_text(encoding="utf-8"))

    assert data["version"] == 1
    assert data["locale"] == "pt-PT"
    assert data["guides_hub"] == "/guias/"

    clusters = data["clusters"]
    topics = data["topics"]

    assert len(clusters) >= 6
    assert len(topics) >= 40

    cluster_ids = [cluster["id"] for cluster in clusters]
    topic_ids = [topic["id"] for topic in topics]
    topic_paths = [topic["path"] for topic in topics]

    assert len(cluster_ids) == len(set(cluster_ids))
    assert len(topic_ids) == len(set(topic_ids))
    assert len(topic_paths) == len(set(topic_paths))

    assert {"cities", "prices", "planning", "objects", "packing", "rights"} <= set(
        cluster_ids
    )

    topic_id_set = set(topic_ids)
    cluster_id_set = set(cluster_ids)

    for topic in topics:
        required_fields = {
            "id",
            "cluster",
            "title",
            "slug",
            "path",
            "primary_query",
            "intent",
            "priority",
            "status",
            "parent",
            "related",
        }

        assert required_fields <= topic.keys(), topic["id"]
        assert topic["cluster"] in cluster_id_set, topic["id"]
        assert topic["status"] in ALLOWED_STATUSES, topic["id"]
        assert set(topic["intent"]) <= ALLOWED_INTENTS, topic["id"]
        assert topic["priority"] in {1, 2, 3}, topic["id"]
        assert topic["path"].startswith("/"), topic["id"]
        assert topic["path"].endswith("/"), topic["id"]
        assert topic["parent"] == "/guias/", topic["id"]
        assert topic["id"] not in topic["related"], topic["id"]

        for related_id in topic["related"]:
            assert related_id in topic_id_set, (
                topic["id"],
                related_id,
            )

        if topic["status"] in {"existing_landing", "published"}:
            relative_path = topic["path"].strip("/")
            expected_file = static_root / relative_path / "index.html"
            assert expected_file.is_file(), (
                topic["id"],
                expected_file,
            )

    required_topics = {
        "mudancas-lisboa",
        "mudancas-porto",
        "mudancas-faro",
        "quanto-custa-uma-mudanca",
        "quanto-custa-mudanca-lisboa",
        "como-preparar-uma-mudanca",
        "como-escolher-empresa-mudancas",
        "transportar-frigorifico",
        "transportar-piano",
        "responsabilidade-danos-mudanca",
    }

    assert required_topics <= topic_id_set

    city_topics = [
        topic
        for topic in topics
        if topic["cluster"] == "cities"
    ]

    assert len(city_topics) >= 20
    assert all("local" in topic["intent"] for topic in city_topics)

    print(
        "GUIDES_TOPICS_REGISTRY_SMOKE_OK",
        len(clusters),
        len(topics),
        len(city_topics),
    )


if __name__ == "__main__":
    main()
