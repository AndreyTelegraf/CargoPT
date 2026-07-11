import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.guide_publish_apply import apply_publication_plan
from scripts.guide_publish_plan import GuidePublicationPlan


def build_plan(root: Path) -> GuidePublicationPlan:
    return GuidePublicationPlan(
        article_id="test-guide",
        public_url=(
            "https://cargopt.pt/guias/precos/test-guide/"
        ),
        output_path=(
            root
            / "static/guias/precos/test-guide/index.html"
        ),
        rendered_html=(
            "<!doctype html>\n"
            "<html><body>Test guide</body></html>\n"
        ),
        registry_text=(
            '{\n'
            '  "topics": [\n'
            '    {"id": "test-guide", "status": "published"}\n'
            '  ]\n'
            '}\n'
        ),
        sitemap_text=(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset>\n'
            '  <url><loc>https://cargopt.pt/guias/precos/'
            'test-guide/</loc></url>\n'
            '</urlset>\n'
        ),
    )


def prepare_files(
    root: Path,
) -> tuple[Path, Path, bytes, bytes]:
    registry_path = root / "content/topics.json"
    sitemap_path = root / "static/sitemap.xml"

    registry_path.parent.mkdir(parents=True)
    sitemap_path.parent.mkdir(parents=True)

    original_registry = (
        b'{\n'
        b'  "topics": [\n'
        b'    {"id": "test-guide", "status": "planned"}\n'
        b'  ]\n'
        b'}\n'
    )
    original_sitemap = (
        b'<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<urlset>\n'
        b'</urlset>\n'
    )

    registry_path.write_bytes(original_registry)
    sitemap_path.write_bytes(original_sitemap)

    return (
        registry_path,
        sitemap_path,
        original_registry,
        original_sitemap,
    )


def exercise_success() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-publish-apply-success-"
    ) as temp_dir:
        root = Path(temp_dir)
        plan = build_plan(root)
        (
            registry_path,
            sitemap_path,
            original_registry,
            original_sitemap,
        ) = prepare_files(root)

        apply_publication_plan(
            plan,
            registry_path=registry_path,
            sitemap_path=sitemap_path,
        )

        if plan.output_path.read_text(
            encoding="utf-8"
        ) != plan.rendered_html:
            raise AssertionError("published HTML differs")

        if registry_path.read_text(
            encoding="utf-8"
        ) != plan.registry_text:
            raise AssertionError("published registry differs")

        if sitemap_path.read_text(
            encoding="utf-8"
        ) != plan.sitemap_text:
            raise AssertionError("published sitemap differs")

        if registry_path.read_bytes() == original_registry:
            raise AssertionError("registry was not updated")

        if sitemap_path.read_bytes() == original_sitemap:
            raise AssertionError("sitemap was not updated")


def exercise_existing_output_failure() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-publish-apply-existing-"
    ) as temp_dir:
        root = Path(temp_dir)
        plan = build_plan(root)
        registry_path, sitemap_path, _, _ = prepare_files(root)

        plan.output_path.parent.mkdir(parents=True)
        plan.output_path.write_text(
            "existing\n",
            encoding="utf-8",
        )

        try:
            apply_publication_plan(
                plan,
                registry_path=registry_path,
                sitemap_path=sitemap_path,
            )
        except ValueError as error:
            if "already exists before apply" not in str(error):
                raise
        else:
            raise AssertionError(
                "expected existing output failure"
            )


def exercise_registry_write_failure_rollback() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-publish-apply-registry-failure-"
    ) as temp_dir:
        root = Path(temp_dir)
        plan = build_plan(root)
        (
            registry_path,
            sitemap_path,
            original_registry,
            original_sitemap,
        ) = prepare_files(root)

        real_atomic_write_text = (
            __import__(
                "scripts.guide_publish_apply",
                fromlist=["atomic_write_text"],
            ).atomic_write_text
        )
        call_count = 0

        def fail_second_write(path, text, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 2:
                raise OSError("simulated registry write failure")

            return real_atomic_write_text(
                path,
                text,
                **kwargs,
            )

        with patch(
            "scripts.guide_publish_apply.atomic_write_text",
            side_effect=fail_second_write,
        ):
            try:
                apply_publication_plan(
                    plan,
                    registry_path=registry_path,
                    sitemap_path=sitemap_path,
                )
            except OSError as error:
                if str(error) != (
                    "simulated registry write failure"
                ):
                    raise
            else:
                raise AssertionError(
                    "expected registry write failure"
                )

        if plan.output_path.exists():
            raise AssertionError(
                "HTML remained after registry failure"
            )

        if registry_path.read_bytes() != original_registry:
            raise AssertionError(
                "registry changed after registry failure"
            )

        if sitemap_path.read_bytes() != original_sitemap:
            raise AssertionError(
                "sitemap changed after registry failure"
            )


def exercise_sitemap_write_failure_rollback() -> None:
    with tempfile.TemporaryDirectory(
        prefix="guide-publish-apply-sitemap-failure-"
    ) as temp_dir:
        root = Path(temp_dir)
        plan = build_plan(root)
        (
            registry_path,
            sitemap_path,
            original_registry,
            original_sitemap,
        ) = prepare_files(root)

        real_atomic_write_text = (
            __import__(
                "scripts.guide_publish_apply",
                fromlist=["atomic_write_text"],
            ).atomic_write_text
        )
        call_count = 0

        def fail_third_write(path, text, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 3:
                raise OSError("simulated sitemap write failure")

            return real_atomic_write_text(
                path,
                text,
                **kwargs,
            )

        with patch(
            "scripts.guide_publish_apply.atomic_write_text",
            side_effect=fail_third_write,
        ):
            try:
                apply_publication_plan(
                    plan,
                    registry_path=registry_path,
                    sitemap_path=sitemap_path,
                )
            except OSError as error:
                if str(error) != (
                    "simulated sitemap write failure"
                ):
                    raise
            else:
                raise AssertionError(
                    "expected sitemap write failure"
                )

        if plan.output_path.exists():
            raise AssertionError(
                "HTML remained after sitemap failure"
            )

        if registry_path.read_bytes() != original_registry:
            raise AssertionError(
                "registry was not rolled back"
            )

        if sitemap_path.read_bytes() != original_sitemap:
            raise AssertionError(
                "sitemap changed after sitemap failure"
            )


def main() -> None:
    exercise_success()
    exercise_existing_output_failure()
    exercise_registry_write_failure_rollback()
    exercise_sitemap_write_failure_rollback()

    print("GUIDE_PUBLISH_APPLY_SMOKE_OK")


if __name__ == "__main__":
    main()
