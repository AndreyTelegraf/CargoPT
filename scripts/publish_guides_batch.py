import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.atomic_write import atomic_write_bytes
from scripts.atomic_write import atomic_write_text
from scripts.guide_publish_plan import GuidePublicationPlan
from scripts.guide_publish_plan import build_publication_plan
from scripts.guide_publish_preflight import DEFAULT_SITEMAP_PATH
from scripts.render_guide import DEFAULT_REGISTRY_PATH
from scripts.render_guide import DEFAULT_STATIC_ROOT


DEFAULT_MANIFEST_PATH = Path("/tmp/cargopt-guide-batch-manifest.json")


@dataclass(frozen=True)
class GuideBatchPublicationPlan:
    plans: tuple[GuidePublicationPlan, ...]
    registry_text: str
    sitemap_text: str


def build_batch_publication_plan(
    *,
    articles: list[dict[str, Any]],
    registry: dict[str, Any],
    sitemap_text: str,
    static_root: Path,
) -> GuideBatchPublicationPlan:
    if not articles:
        raise ValueError("Guide batch must contain at least one article")

    article_ids = [article.get("id") for article in articles]
    article_paths = [article.get("path") for article in articles]

    if len(article_ids) != len(set(article_ids)):
        raise ValueError(f"DUPLICATE_BATCH_ARTICLE_ID:{article_ids}")

    if len(article_paths) != len(set(article_paths)):
        raise ValueError(f"DUPLICATE_BATCH_ARTICLE_PATH:{article_paths}")

    current_registry = json.loads(json.dumps(registry))
    current_sitemap = sitemap_text
    plans: list[GuidePublicationPlan] = []
    output_paths: set[Path] = set()

    for article in articles:
        plan = build_publication_plan(
            article=article,
            registry=current_registry,
            sitemap_text=current_sitemap,
            static_root=static_root,
        )

        if plan.output_path in output_paths:
            raise ValueError(
                f"DUPLICATE_BATCH_OUTPUT_PATH:{plan.output_path}"
            )

        output_paths.add(plan.output_path)
        plans.append(plan)
        current_registry = json.loads(plan.registry_text)
        current_sitemap = plan.sitemap_text

    return GuideBatchPublicationPlan(
        plans=tuple(plans),
        registry_text=plans[-1].registry_text,
        sitemap_text=plans[-1].sitemap_text,
    )


def apply_batch_publication_plan(
    batch: GuideBatchPublicationPlan,
    *,
    registry_path: Path,
    sitemap_path: Path,
    acceptance: Callable[[], None] | None = None,
) -> None:
    registry_path = Path(registry_path)
    sitemap_path = Path(sitemap_path)

    if not registry_path.is_file():
        raise FileNotFoundError(registry_path)

    if not sitemap_path.is_file():
        raise FileNotFoundError(sitemap_path)

    for plan in batch.plans:
        if plan.output_path.exists():
            raise ValueError(
                "Guide output already exists before batch apply: "
                f"{plan.output_path}"
            )

    original_registry = registry_path.read_bytes()
    original_sitemap = sitemap_path.read_bytes()
    written_outputs: list[Path] = []
    registry_written = False
    sitemap_written = False

    try:
        for plan in batch.plans:
            atomic_write_text(
                plan.output_path,
                plan.rendered_html,
            )
            written_outputs.append(plan.output_path)

        atomic_write_text(
            registry_path,
            batch.registry_text,
        )
        registry_written = True

        atomic_write_text(
            sitemap_path,
            batch.sitemap_text,
        )
        sitemap_written = True

        if registry_path.read_text(
            encoding="utf-8"
        ) != batch.registry_text:
            raise RuntimeError(
                "Published registry differs from batch plan"
            )

        if sitemap_path.read_text(
            encoding="utf-8"
        ) != batch.sitemap_text:
            raise RuntimeError(
                "Published sitemap differs from batch plan"
            )

        for plan in batch.plans:
            if plan.output_path.read_text(
                encoding="utf-8"
            ) != plan.rendered_html:
                raise RuntimeError(
                    "Published HTML differs from batch plan: "
                    f"{plan.output_path}"
                )

        if acceptance is not None:
            acceptance()
    except BaseException as original_error:
        rollback_errors: list[BaseException] = []

        if sitemap_written:
            try:
                atomic_write_bytes(sitemap_path, original_sitemap)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if registry_written:
            try:
                atomic_write_bytes(registry_path, original_registry)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        for output_path in reversed(written_outputs):
            try:
                output_path.unlink(missing_ok=True)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if rollback_errors:
            raise RuntimeError(
                "Batch publication failed and rollback was incomplete"
            ) from original_error

        raise


def manifest_for_batch(
    batch: GuideBatchPublicationPlan,
    *,
    registry_path: Path,
    sitemap_path: Path,
    mode: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": mode,
        "article_count": len(batch.plans),
        "articles": [
            {
                "id": plan.article_id,
                "url": plan.public_url,
                "output_path": str(plan.output_path),
                "bytes": len(plan.rendered_html.encode("utf-8")),
            }
            for plan in batch.plans
        ],
        "shared_files": [
            str(Path(registry_path)),
            str(Path(sitemap_path)),
        ],
    }


def run_corpus_acceptance() -> None:
    commands = (
        (
            sys.executable,
            "-m",
            "scripts.validate_internal_link_map",
        ),
        (
            sys.executable,
            "-m",
            "scripts.corpus_release_audit",
            "--text-report",
            "/tmp/cargopt-guide-batch-corpus-audit.txt",
            "--json-report",
            "/tmp/cargopt-guide-batch-corpus-audit.json",
        ),
    )

    for command in commands:
        subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=True,
        )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Publish multiple CargoPT guides as one in-memory "
            "preflight and transactional apply."
        )
    )
    parser.add_argument(
        "articles",
        nargs="+",
        type=Path,
        help="Structured guide article JSON files.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
    )
    parser.add_argument(
        "--sitemap",
        type=Path,
        default=DEFAULT_SITEMAP_PATH,
    )
    parser.add_argument(
        "--static-root",
        type=Path,
        default=DEFAULT_STATIC_ROOT,
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build every plan and write only the manifest.",
    )
    parser.add_argument(
        "--skip-acceptance",
        action="store_true",
        help=(
            "Skip canonical link-map and corpus release acceptance. "
            "Intended only for isolated fixtures."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if len(args.articles) != len(set(args.articles)):
        raise ValueError("DUPLICATE_BATCH_ARTICLE_FILE")

    for path in args.articles:
        if not path.is_file():
            raise FileNotFoundError(path)

    registry = load_json(args.registry)
    sitemap_text = args.sitemap.read_text(encoding="utf-8")
    articles = [load_json(path) for path in args.articles]

    batch = build_batch_publication_plan(
        articles=articles,
        registry=registry,
        sitemap_text=sitemap_text,
        static_root=args.static_root,
    )

    mode = "check" if args.check else "applied"
    manifest = manifest_for_batch(
        batch,
        registry_path=args.registry,
        sitemap_path=args.sitemap,
        mode=mode,
    )

    if not args.check:
        apply_batch_publication_plan(
            batch,
            registry_path=args.registry,
            sitemap_path=args.sitemap,
            acceptance=(
                None
                if args.skip_acceptance
                else run_corpus_acceptance
            ),
        )

    atomic_write_text(
        args.manifest,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )

    print(
        "GUIDE_BATCH_CHECK_OK" if args.check else "GUIDE_BATCH_PUBLISHED",
        len(batch.plans),
        args.manifest,
    )


if __name__ == "__main__":
    main()
