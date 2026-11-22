"""One ragcourt at a time per working folder (D-057): two runs writing the same question file and cache
would duplicate entries without a word.

A file ``lock`` holds the process id while a command that writes runs; a lock left by a process that no
longer exists is taken over.
"""

from __future__ import annotations

import os
import time
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from ragcourt.errors import ConfigError

LOCK = "lock"
STARTING_SECONDS = 10.0


@contextmanager
def workdir_lock(workdir: Path) -> Generator[None]:
    """Hold the working folder's lock for the duration of the block."""
    workdir.mkdir(parents=True, exist_ok=True)
    path = workdir / LOCK
    _take(path)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def _take(path: Path) -> None:
    try:
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        _refuse_or_clear(path)
        handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(handle, "w", encoding="utf-8") as file:
        file.write(str(os.getpid()))


def _refuse_or_clear(path: Path) -> None:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    pid = int(text) if text.isdigit() else 0
    starting = not text and time.time() - path.stat().st_mtime < STARTING_SECONDS  # its id is being written
    if starting or (pid and _alive(pid)):
        raise ConfigError(
            f"Another ragcourt (process {pid or 'starting'}) is using {path.parent}; wait for it to finish, "
            "or give this "
            f"one another --workdir. If no other ragcourt runs, delete {path}."
        )
    path.unlink(missing_ok=True)


def _alive(pid: int) -> bool:
    if os.name != "posix":  # os.kill(pid, 0) would stop the process on Windows: assume it runs
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True
