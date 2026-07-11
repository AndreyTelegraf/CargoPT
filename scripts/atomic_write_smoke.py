import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.atomic_write import atomic_write_bytes
from scripts.atomic_write import atomic_write_text


def temporary_files(directory: Path, target_name: str) -> list[Path]:
    return sorted(directory.glob(f".{target_name}.*.tmp"))


def exercise_new_text_file(root: Path) -> None:
    target = root / "nested" / "new.txt"
    content = "Olá, CargoPT.\nSegunda linha.\n"

    atomic_write_text(target, content)

    if target.read_text(encoding="utf-8") != content:
        raise AssertionError("new text file content differs")

    if stat.S_IMODE(target.stat().st_mode) != 0o644:
        raise AssertionError(
            f"unexpected new file mode: "
            f"{oct(stat.S_IMODE(target.stat().st_mode))}"
        )

    leftovers = temporary_files(target.parent, target.name)

    if leftovers:
        raise AssertionError(f"temporary files remain: {leftovers}")


def exercise_existing_text_replacement(root: Path) -> None:
    target = root / "existing.txt"
    target.write_text("old content\n", encoding="utf-8")
    os.chmod(target, 0o640)

    original_inode = target.stat().st_ino
    replacement = "new content\n"

    atomic_write_text(target, replacement)

    if target.read_text(encoding="utf-8") != replacement:
        raise AssertionError("replacement content differs")

    if target.stat().st_ino == original_inode:
        raise AssertionError("target was modified in place")

    if stat.S_IMODE(target.stat().st_mode) != 0o640:
        raise AssertionError(
            f"existing file mode was not preserved: "
            f"{oct(stat.S_IMODE(target.stat().st_mode))}"
        )

    leftovers = temporary_files(target.parent, target.name)

    if leftovers:
        raise AssertionError(f"temporary files remain: {leftovers}")


def exercise_binary_file(root: Path) -> None:
    target = root / "binary.dat"
    content = bytes(range(256))

    atomic_write_bytes(target, content)

    if target.read_bytes() != content:
        raise AssertionError("binary file content differs")

    leftovers = temporary_files(target.parent, target.name)

    if leftovers:
        raise AssertionError(f"temporary files remain: {leftovers}")


def exercise_replace_failure_cleanup(root: Path) -> None:
    target = root / "failure.txt"
    original = b"original bytes\n"
    replacement = b"replacement bytes\n"

    target.write_bytes(original)

    with patch(
        "scripts.atomic_write.os.replace",
        side_effect=OSError("simulated replace failure"),
    ):
        try:
            atomic_write_bytes(target, replacement)
        except OSError as error:
            if str(error) != "simulated replace failure":
                raise
        else:
            raise AssertionError("expected simulated replace failure")

    if target.read_bytes() != original:
        raise AssertionError(
            "existing target changed after failed replacement"
        )

    leftovers = temporary_files(target.parent, target.name)

    if leftovers:
        raise AssertionError(
            f"temporary file was not cleaned after failure: {leftovers}"
        )


def exercise_write_failure_cleanup(root: Path) -> None:
    target = root / "write-failure.txt"

    with patch(
        "scripts.atomic_write.os.fsync",
        side_effect=OSError("simulated fsync failure"),
    ):
        try:
            atomic_write_text(target, "must not be published\n")
        except OSError as error:
            if str(error) != "simulated fsync failure":
                raise
        else:
            raise AssertionError("expected simulated fsync failure")

    if target.exists():
        raise AssertionError(
            "target appeared after failed temporary-file fsync"
        )

    leftovers = temporary_files(target.parent, target.name)

    if leftovers:
        raise AssertionError(
            f"temporary file was not cleaned after fsync failure: "
            f"{leftovers}"
        )


def main() -> None:
    with tempfile.TemporaryDirectory(
        prefix="atomic-write-smoke-"
    ) as temporary_directory:
        root = Path(temporary_directory)

        exercise_new_text_file(root)
        exercise_existing_text_replacement(root)
        exercise_binary_file(root)
        exercise_replace_failure_cleanup(root)
        exercise_write_failure_cleanup(root)

    print("ATOMIC_WRITE_SMOKE_OK")


if __name__ == "__main__":
    main()
