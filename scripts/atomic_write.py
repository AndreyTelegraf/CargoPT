import os
import stat
import tempfile
from pathlib import Path


DEFAULT_FILE_MODE = 0o644


def _target_mode(path: Path) -> int:
    if not path.exists():
        return DEFAULT_FILE_MODE

    return stat.S_IMODE(path.stat().st_mode)


def _fsync_directory(path: Path) -> None:
    directory_fd = os.open(path, os.O_RDONLY)

    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = _target_mode(path)
    file_descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(data)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.chmod(temporary_path, mode)
        os.replace(temporary_path, path)
        _fsync_directory(path.parent)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
) -> None:
    atomic_write_bytes(
        path,
        text.encode(encoding),
    )
