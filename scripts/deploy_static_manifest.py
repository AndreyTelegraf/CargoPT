import argparse
import hashlib
import json
import os
import shutil
import stat
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


DEFAULT_WEBROOT = Path("/var/www/cargopt.pt")


@dataclass(frozen=True)
class StaticDeployment:
    source: Path
    target: Path
    public_path: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_path_for(relative: Path) -> str:
    value = relative.as_posix()
    if value == "index.html":
        return "/"
    if value.endswith("/index.html"):
        return "/" + value.removesuffix("index.html")
    return "/" + value


def load_deployments(
    manifest_path: Path,
    webroot: Path,
) -> tuple[dict, list[StaticDeployment]]:
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    if manifest.get("schema_version") != 1:
        raise ValueError("UNSUPPORTED_STATIC_MANIFEST_SCHEMA")

    if manifest.get("mode") != "applied":
        raise ValueError("STATIC_MANIFEST_NOT_APPLIED")

    static_root = Path(manifest["static_root"]).resolve()
    webroot = webroot.resolve()
    raw_files = manifest.get("static_files")

    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("EMPTY_STATIC_MANIFEST")

    sources = [Path(value).resolve() for value in raw_files]
    if len(sources) != len(set(sources)):
        raise ValueError("DUPLICATE_STATIC_MANIFEST_FILE")

    deployments = []
    for source in sources:
        if not source.is_file():
            raise FileNotFoundError(source)
        relative = source.relative_to(static_root)
        target = (webroot / relative).resolve()
        target.relative_to(webroot)
        deployments.append(
            StaticDeployment(
                source=source,
                target=target,
                public_path=public_path_for(relative),
            )
        )

    return manifest, deployments


def atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".deploy",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        shutil.copyfile(source, temporary)
        os.chmod(
            temporary,
            stat.S_IMODE(source.stat().st_mode),
        )
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def verify_live(
    deployments: list[StaticDeployment],
    *,
    public_base_url: str,
) -> None:
    for deployment in deployments:
        request = urllib.request.Request(
            public_base_url.rstrip("/")
            + deployment.public_path
            + "?manifest_deploy_verify=1",
            headers={
                "User-Agent": "CargoPT manifest deploy verification",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(
            request,
            timeout=20,
        ) as response:
            if response.status != 200:
                raise RuntimeError(
                    "LIVE_STATIC_STATUS_MISMATCH:"
                    f"{deployment.public_path}:{response.status}"
                )


def deploy_static_manifest(
    deployments: list[StaticDeployment],
    *,
    verify_live_callback: Callable[[], None] | None,
) -> Path:
    backup_root = Path(
        tempfile.mkdtemp(prefix="cargopt-static-deploy-")
    )
    existed: dict[Path, bool] = {}
    installed: list[StaticDeployment] = []

    try:
        for index, deployment in enumerate(deployments):
            target_exists = deployment.target.is_file()
            existed[deployment.target] = target_exists
            if target_exists:
                backup = backup_root / str(index)
                shutil.copy2(deployment.target, backup)

        for deployment in deployments:
            atomic_copy(deployment.source, deployment.target)
            installed.append(deployment)
            if sha256(deployment.source) != sha256(deployment.target):
                raise RuntimeError(
                    f"STATIC_PARITY_MISMATCH:{deployment.target}"
                )

        if verify_live_callback is not None:
            verify_live_callback()
    except BaseException as original_error:
        rollback_errors: list[BaseException] = []
        for index, deployment in reversed(
            list(enumerate(deployments))
        ):
            try:
                if existed.get(deployment.target):
                    atomic_copy(
                        backup_root / str(index),
                        deployment.target,
                    )
                else:
                    deployment.target.unlink(missing_ok=True)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)

        if rollback_errors:
            raise RuntimeError(
                "Static deploy failed and rollback was incomplete"
            ) from original_error
        raise

    return backup_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Deploy only static files listed by an applied CargoPT "
            "guide batch manifest, with parity and rollback."
        )
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--webroot",
        type=Path,
        default=DEFAULT_WEBROOT,
    )
    parser.add_argument(
        "--public-base-url",
        default="https://cargopt.pt",
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-live", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _, deployments = load_deployments(
        args.manifest,
        args.webroot,
    )

    if args.check:
        print("STATIC_MANIFEST_DEPLOY_CHECK_OK", len(deployments))
        return

    backup = deploy_static_manifest(
        deployments,
        verify_live_callback=(
            None
            if args.skip_live
            else lambda: verify_live(
                deployments,
                public_base_url=args.public_base_url,
            )
        ),
    )
    print(
        "STATIC_MANIFEST_DEPLOY_OK",
        len(deployments),
        backup,
    )


if __name__ == "__main__":
    main()
