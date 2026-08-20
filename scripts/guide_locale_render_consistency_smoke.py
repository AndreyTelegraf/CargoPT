from __future__ import annotations

import json
from pathlib import Path

from scripts.render_guide import output_path_for_article
from scripts.render_guide import render_guide


ROOT = Path(__file__).resolve().parents[1]
ARTICLES_ROOT = ROOT / "content/guides/articles"
STATIC_ROOT = ROOT / "app/static"
REGISTRY_PATH = ROOT / "content/guides/topics.json"


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    drifted: list[str] = []
    checked = 0

    for article_path in sorted(ARTICLES_ROOT.glob("*.json")):
        article = json.loads(article_path.read_text(encoding="utf-8"))
        if article["locale"] not in {"en", "ru"}:
            continue

        output_path = output_path_for_article(article, STATIC_ROOT)
        rendered = render_guide(article, registry)
        checked += 1

        if not output_path.exists() or output_path.read_text(encoding="utf-8") != rendered:
            drifted.append(article_path.name)

    assert not drifted, (len(drifted), drifted[:20])
    print("GUIDE_LOCALE_RENDER_CONSISTENCY_OK", checked)


if __name__ == "__main__":
    main()
