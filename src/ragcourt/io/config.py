"""Reading ``ragcourt.toml``, the one optional configuration file of a project (design §3.3).

Every setting has a default, so the file is optional. A key ragcourt does not know is an error that names
the keys it does know, so a typo never silently does nothing (D-039). Each milestone step adds the
settings it uses here: one field, one line in ``KNOWN_KEYS`` and one line in ``load_config``.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ragcourt.errors import ConfigError

CONFIG_FILE = "ragcourt.toml"
KNOWN_KEYS = {
    "stages_dir": "the folder of your own stages (design §7.2)",
}


@dataclass(frozen=True)
class Config:
    """A project's settings. ``file`` is the ``ragcourt.toml`` they came from, or None for the defaults."""

    file: Path | None
    stages_dir: Path


def load_config(project: Path) -> Config:
    """The settings of the project in ``project``: its ``ragcourt.toml`` over the defaults."""
    path = project / CONFIG_FILE
    if not path.is_file():
        return Config(file=None, stages_dir=project / "ragcourt_stages")
    table = _read_toml(path)
    _check_keys(table, path)
    stages_dir = _text(table, "stages_dir", "ragcourt_stages", path)
    return Config(file=path, stages_dir=project / stages_dir)


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ConfigError(f"{path} is not UTF-8 (byte {error.start}). Save it as UTF-8.") from error
    except OSError as error:
        raise ConfigError(f"{path} cannot be read: {error.strerror or error}.") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} is not valid TOML: {error}. Fix that line.") from error


def _check_keys(table: dict[str, Any], path: Path) -> None:
    unknown = sorted(set(table) - set(KNOWN_KEYS))
    if unknown:
        known = "; ".join(f"{key}: {meaning}" for key, meaning in KNOWN_KEYS.items())
        raise ConfigError(f"{path}: unknown setting {', '.join(unknown)}. The settings are: {known}.")


def _text(table: dict[str, Any], key: str, default: str, path: Path) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path}: {key} must be a non-empty string, not {value!r}.")
    return value
