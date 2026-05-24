"""Atomic file write helpers."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


class SafeWriteError(RuntimeError):
    """Raised when an atomic write cannot be completed."""


_LOCKS: dict[Path, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _path_lock(path: Path) -> threading.Lock:
    key = path.resolve(strict=False)
    with _LOCKS_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def _prepare_parent(path: Path, make_parents: bool) -> None:
    parent = path.parent
    if make_parents:
        parent.mkdir(parents=True, exist_ok=True)
    elif not parent.exists():
        raise SafeWriteError(f"Parent directory does not exist: {parent}")


def safe_write_bytes(
    path: str | os.PathLike[str],
    data: bytes,
    *,
    make_parents: bool = True,
    file_mode: int | None = None,
    lock: bool = False,
) -> Path:
    """Atomically write bytes to a file and return the target path."""
    target = Path(path)

    def _write() -> Path:
        _prepare_parent(target, make_parents)
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(target.parent),
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp_name = tmp.name
                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
            if file_mode is not None:
                os.chmod(tmp_name, file_mode)
            os.replace(tmp_name, target)
            return target
        except Exception as exc:
            if tmp_name:
                try:
                    os.unlink(tmp_name)
                except FileNotFoundError:
                    pass
            if isinstance(exc, SafeWriteError):
                raise
            raise SafeWriteError(f"safe write failed for {target}: {exc}") from exc

    if lock:
        with _path_lock(target):
            return _write()
    return _write()


def safe_write_text(
    path: str | os.PathLike[str],
    text: str,
    *,
    encoding: str = "utf-8",
    make_parents: bool = True,
    file_mode: int | None = None,
    lock: bool = False,
) -> Path:
    """Atomically write text to a file and return the target path."""
    return safe_write_bytes(
        path,
        text.encode(encoding),
        make_parents=make_parents,
        file_mode=file_mode,
        lock=lock,
    )


def safe_write_json(
    path: str | os.PathLike[str],
    data: Any,
    *,
    ensure_ascii: bool = True,
    indent: int | None = 2,
    make_parents: bool = True,
    file_mode: int | None = None,
    lock: bool = False,
) -> Path:
    """Serialize JSON first, then atomically write it to disk."""
    try:
        payload = json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise SafeWriteError(f"JSON serialization failed: {exc}") from exc
    return safe_write_text(
        path,
        payload,
        make_parents=make_parents,
        file_mode=file_mode,
        lock=lock,
    )


def safe_append_text(
    path: str | os.PathLike[str],
    text: str,
    *,
    encoding: str = "utf-8",
    make_parents: bool = True,
    file_mode: int | None = None,
) -> Path:
    """Append text under a per-file lock."""
    target = Path(path)
    with _path_lock(target):
        try:
            _prepare_parent(target, make_parents)
            with target.open("a", encoding=encoding) as fh:
                fh.write(text)
                fh.flush()
                os.fsync(fh.fileno())
            if file_mode is not None:
                os.chmod(target, file_mode)
            return target
        except Exception as exc:
            if isinstance(exc, SafeWriteError):
                raise
            raise SafeWriteError(f"safe append failed for {target}: {exc}") from exc
