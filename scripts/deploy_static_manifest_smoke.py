import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.deploy_static_manifest import deploy_static_manifest
from scripts.deploy_static_manifest import load_deployments


def prepare(root: Path) -> tuple[Path, Path, Path]:
    static_root = root / "static"
    webroot = root / "webroot"
    first = static_root / "en/guides/one/index.html"
    second = static_root / "ru/guides/two/index.html"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_text("new one\n", encoding="utf-8")
    second.write_text("new two\n", encoding="utf-8")
    old_first = webroot / "en/guides/one/index.html"
    old_first.parent.mkdir(parents=True)
    old_first.write_text("old one\n", encoding="utf-8")
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "mode": "applied",
                "static_root": str(static_root),
                "static_files": [str(first), str(second)],
            }
        ),
        encoding="utf-8",
    )
    return manifest, static_root, webroot


def exercise_success() -> None:
    with tempfile.TemporaryDirectory(
        prefix="static-manifest-success-"
    ) as temp_dir:
        root = Path(temp_dir)
        manifest, _, webroot = prepare(root)
        _, deployments = load_deployments(manifest, webroot)
        deploy_static_manifest(
            deployments,
            verify_live_callback=lambda: None,
        )
        if (
            webroot / "en/guides/one/index.html"
        ).read_text() != "new one\n":
            raise AssertionError("existing file was not replaced")
        if (
            webroot / "ru/guides/two/index.html"
        ).read_text() != "new two\n":
            raise AssertionError("new file was not deployed")


def exercise_live_failure_rollback() -> None:
    with tempfile.TemporaryDirectory(
        prefix="static-manifest-live-failure-"
    ) as temp_dir:
        root = Path(temp_dir)
        manifest, _, webroot = prepare(root)
        _, deployments = load_deployments(manifest, webroot)

        def fail_live() -> None:
            raise RuntimeError("simulated live failure")

        try:
            deploy_static_manifest(
                deployments,
                verify_live_callback=fail_live,
            )
        except RuntimeError as error:
            if str(error) != "simulated live failure":
                raise
        else:
            raise AssertionError("expected live verification failure")

        if (
            webroot / "en/guides/one/index.html"
        ).read_text() != "old one\n":
            raise AssertionError("existing file was not restored")
        if (
            webroot / "ru/guides/two/index.html"
        ).exists():
            raise AssertionError("new file remained after rollback")


def exercise_copy_failure_rollback() -> None:
    with tempfile.TemporaryDirectory(
        prefix="static-manifest-copy-failure-"
    ) as temp_dir:
        root = Path(temp_dir)
        manifest, _, webroot = prepare(root)
        _, deployments = load_deployments(manifest, webroot)
        module = __import__(
            "scripts.deploy_static_manifest",
            fromlist=["atomic_copy"],
        )
        real_copy = module.atomic_copy
        calls = 0

        def fail_second_copy(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated copy failure")
            return real_copy(source, target)

        with patch(
            "scripts.deploy_static_manifest.atomic_copy",
            side_effect=fail_second_copy,
        ):
            try:
                deploy_static_manifest(
                    deployments,
                    verify_live_callback=None,
                )
            except OSError as error:
                if str(error) != "simulated copy failure":
                    raise
            else:
                raise AssertionError("expected copy failure")

        if (
            webroot / "en/guides/one/index.html"
        ).read_text() != "old one\n":
            raise AssertionError("copy failure did not restore existing")
        if (
            webroot / "ru/guides/two/index.html"
        ).exists():
            raise AssertionError("copy failure left new file")


def main() -> None:
    exercise_success()
    exercise_live_failure_rollback()
    exercise_copy_failure_rollback()
    print("DEPLOY_STATIC_MANIFEST_SMOKE_OK")


if __name__ == "__main__":
    main()
