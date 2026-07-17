import copy
import json
from pathlib import Path

from scripts.corpus_release_audit import Audit
from scripts.corpus_release_audit import validate_article_structure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARTICLE = (
    PROJECT_ROOT
    / "content/guides/articles/quanto-custa-uma-mudanca.json"
)


def load_source_article() -> dict:
    return json.loads(
        SOURCE_ARTICLE.read_text(encoding="utf-8")
    )


def error_codes(audit: Audit) -> list[str]:
    return [
        finding.code
        for finding in audit.findings
        if finding.severity == "error"
    ]


def require_no_errors(
    article: dict,
    *,
    filename: str,
) -> None:
    audit = Audit()

    validate_article_structure(
        audit,
        path=Path(filename),
        article=article,
    )

    codes = error_codes(audit)

    if codes:
        raise AssertionError(
            f"unexpected valid multilingual errors: {codes}"
        )


def main() -> None:
    existing_pt = load_source_article()

    require_no_errors(
        existing_pt,
        filename="existing-pt.json",
    )

    multilingual_en = copy.deepcopy(existing_pt)
    multilingual_en["id"] = "leave-portugal-en"
    multilingual_en["locale"] = "en"
    multilingual_en["path"] = (
        "/en/guides/how-to-leave-portugal/"
    )
    multilingual_en["translation_group"] = "leave-portugal"
    multilingual_en["alternates"] = {
        "en": "/en/guides/how-to-leave-portugal/",
        "ru": (
            "/ru/guides/"
            "kak-pravilno-uehat-iz-portugalii/"
        ),
        "pt-BR": (
            "/pt-br/guias/"
            "como-sair-de-portugal/"
        ),
    }

    require_no_errors(
        multilingual_en,
        filename="leave-portugal-en.json",
    )

    multilingual_ru = copy.deepcopy(multilingual_en)
    multilingual_ru["id"] = "leave-portugal-ru"
    multilingual_ru["locale"] = "ru"
    multilingual_ru["path"] = (
        "/ru/guides/"
        "kak-pravilno-uehat-iz-portugalii/"
    )

    require_no_errors(
        multilingual_ru,
        filename="leave-portugal-ru.json",
    )

    multilingual_br = copy.deepcopy(multilingual_en)
    multilingual_br["id"] = "leave-portugal-pt-br"
    multilingual_br["locale"] = "pt-BR"
    multilingual_br["path"] = (
        "/pt-br/guias/como-sair-de-portugal/"
    )

    require_no_errors(
        multilingual_br,
        filename="leave-portugal-pt-br.json",
    )

    print(
        "CORPUS_MULTILINGUAL_ARTICLE_CONTRACT_SMOKE_OK",
        4,
    )


if __name__ == "__main__":
    main()
