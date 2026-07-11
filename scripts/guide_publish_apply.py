from pathlib import Path

from scripts.atomic_write import atomic_write_bytes
from scripts.atomic_write import atomic_write_text
from scripts.guide_publish_plan import GuidePublicationPlan


def apply_publication_plan(
    plan: GuidePublicationPlan,
    *,
    registry_path: Path,
    sitemap_path: Path,
) -> None:
    registry_path = Path(registry_path)
    sitemap_path = Path(sitemap_path)
    output_path = Path(plan.output_path)

    if output_path.exists():
        raise ValueError(
            f"Guide output already exists before apply: {output_path}"
        )

    if not registry_path.is_file():
        raise FileNotFoundError(registry_path)

    if not sitemap_path.is_file():
        raise FileNotFoundError(sitemap_path)

    original_registry = registry_path.read_bytes()
    original_sitemap = sitemap_path.read_bytes()

    output_written = False
    registry_written = False
    sitemap_written = False

    try:
        atomic_write_text(
            output_path,
            plan.rendered_html,
        )
        output_written = True

        atomic_write_text(
            registry_path,
            plan.registry_text,
        )
        registry_written = True

        atomic_write_text(
            sitemap_path,
            plan.sitemap_text,
        )
        sitemap_written = True
    except BaseException as original_error:
        rollback_errors: list[BaseException] = []

        if sitemap_written:
            try:
                atomic_write_bytes(
                    sitemap_path,
                    original_sitemap,
                )
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if registry_written:
            try:
                atomic_write_bytes(
                    registry_path,
                    original_registry,
                )
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if output_written:
            try:
                output_path.unlink(missing_ok=True)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if rollback_errors:
            raise RuntimeError(
                "Publication apply failed and rollback was incomplete"
            ) from original_error

        raise

    if not output_written:
        raise RuntimeError("Guide HTML was not written")

    if not registry_written:
        raise RuntimeError("Guide registry was not written")

    if not sitemap_written:
        raise RuntimeError("Guide sitemap was not written")
