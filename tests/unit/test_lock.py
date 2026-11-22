"""One ragcourt at a time per working folder (D-057)."""

import os
from pathlib import Path

import pytest

from ragcourt import ConfigError
from ragcourt.io.lock import LOCK, workdir_lock


def test_a_second_ragcourt_is_refused_and_a_stale_lock_is_taken_over(tmp_path: Path) -> None:
    with workdir_lock(tmp_path):
        assert (tmp_path / LOCK).read_text() == str(os.getpid())
        with pytest.raises(ConfigError, match="Another ragcourt"), workdir_lock(tmp_path):
            pass  # pragma: no cover
    assert not (tmp_path / LOCK).exists()
    (tmp_path / LOCK).write_text("999999999")  # no such process
    with workdir_lock(tmp_path):
        assert (tmp_path / LOCK).read_text() == str(os.getpid())
