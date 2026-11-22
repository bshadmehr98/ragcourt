"""Reading ``ragcourt.toml``, the one optional configuration file of a project (design §3.3, §11.4).

Every setting has a default, so the file is optional. A key ragcourt does not know is an error that names
the keys it does know, so a typo never silently does nothing (D-039). Keys are never written in the file:
an endpoint names the environment variable that holds its key.
"""

from __future__ import annotations

import tomllib
from dataclasses import fields
from pathlib import Path
from typing import Any, cast

from ragcourt.errors import ConfigError
from ragcourt.types.audit import AuditSettings
from ragcourt.types.config import ROLES, Budget, Config, Endpoint, QuestionSettings, Role, SearchSettings

CONFIG_FILE = "ragcourt.toml"
Table = dict[str, Any]
TOP_KEYS = {
    "stages_dir": "the folder of your own stages (design §7.2)",
    "seed": "the seed of every random choice",
    "ollama_url": "where Ollama answers (default http://localhost:11434)",
    "prompts_dir": "a folder of your own prompt files (design §6.6)",
    "models": "[models]: the model of each role (writer, judge, embedders, reranker, doctor)",
    "endpoints": "[endpoints.NAME]: an OpenAI-compatible endpoint (base_url, api_key_env)",
    "prices": "[prices]: dollars per million tokens, by model",
    "questions": "[questions]: per_category, categories, min_held_out, window_chars",
    "search": "[search]: chunkers, retrievers, rerankers, metric, k, depth, budget_tokens",
    "audit": "[audit]: the thresholds of the checks",
    "budget": "[budget]: usd, minutes",
}
ENDPOINT_KEYS = {"base_url": "the endpoint's URL", "api_key_env": "the environment variable holding its key"}


def load_config(project: Path, file: Path | None = None) -> Config:
    """The settings of the project in ``project``: its ``ragcourt.toml`` (or ``file``) over the defaults."""
    path = file or project / CONFIG_FILE
    if not path.is_file():
        if file is not None:
            raise ConfigError(f"The configuration file {file} does not exist.")
        return Config(project=project)
    table = read_toml(path)
    _check_keys(table, TOP_KEYS, str(path))
    return Config(
        project=project,
        file=path,
        stages_dir=_folder(table, "stages_dir", project, path),
        seed=_typed(table, "seed", 0, int, path),
        ollama_url=_text(table, "ollama_url", "http://localhost:11434", path).rstrip("/"),
        roles=_roles(_section(table, "models", path), path),
        endpoints=_endpoints(_section(table, "endpoints", path), path),
        prices=_prices(_section(table, "prices", path), path),
        questions=_settings(QuestionSettings, _section(table, "questions", path), path, "questions"),
        search=_settings(SearchSettings, _section(table, "search", path), path, "search"),
        audit=_settings(AuditSettings, _section(table, "audit", path), path, "audit"),
        budget=_settings(Budget, _section(table, "budget", path), path, "budget"),
        prompts_dir=_folder(table, "prompts_dir", project, path),
    )


def read_toml(path: Path) -> Table:
    """The TOML table of ``path``, or a ``ConfigError`` that says what is wrong."""
    try:
        return tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError as error:
        raise ConfigError(f"{path} is not UTF-8 (byte {error.start}). Save it as UTF-8.") from error
    except OSError as error:
        raise ConfigError(f"{path} cannot be read: {error.strerror or error}.") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} is not valid TOML: {error}. Fix that line.") from error


def _check_keys(table: Table, known: dict[str, str], where: str) -> None:
    unknown = sorted(set(table) - set(known))
    if unknown:
        listing = "; ".join(f"{key}: {meaning}" for key, meaning in known.items())
        raise ConfigError(f"{where}: unknown setting {', '.join(unknown)}. The settings are: {listing}.")


def _section(table: Table, key: str, path: Path) -> Table:
    value = table.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: {key} must be a table, [{key}].")
    return cast(Table, value)


def _folder(table: Table, key: str, project: Path, path: Path) -> Path | None:
    if key not in table:
        return None
    return project / _text(table, key, "", path)


def _typed(table: Table, key: str, default: Any, kind: type, path: Path) -> Any:
    value = table.get(key, default)
    if kind is float and isinstance(value, int) and not isinstance(value, bool):
        return float(value)
    wrong_kind = not isinstance(value, kind) or isinstance(value, bool) != (kind is bool)
    if value is not None and wrong_kind:
        raise ConfigError(f"{path}: {key} must be {kind.__name__}, not {value!r}.")
    return value


def _text(table: Table, key: str, default: str, path: Path) -> str:
    value = table.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{path}: {key} must be a non-empty string, not {value!r}.")
    return value


def _names(value: Any, key: str, path: Path) -> tuple[str, ...]:
    """A list of names, or one string of names separated by commas."""
    if isinstance(value, str):
        value = [part.strip() for part in value.split(",")]
    items = cast(list[Any], value) if isinstance(value, list) else None
    if items is None or not items or not all(isinstance(item, str) and item for item in items):
        raise ConfigError(f"{path}: {key} must be a list of names, not {value!r}.")
    return tuple(str(item) for item in items)


def _roles(section: Table, path: Path) -> dict[str, Role]:
    known: dict[str, str] = dict.fromkeys(ROLES, "a model name (a list for embedders)")
    _check_keys(section, known, f"{path} [models]")
    roles: dict[str, Role] = {}
    for role, value in section.items():
        roles[role] = Role(role, _names(value, f"models.{role}", path), str(path))
    return roles


def _endpoints(section: Table, path: Path) -> dict[str, Endpoint]:
    endpoints: dict[str, Endpoint] = {}
    for name in section:
        table = _section(section, name, path)
        _check_keys(table, ENDPOINT_KEYS, f"{path} [endpoints.{name}]")
        base_url = _text(table, "base_url", "", path).rstrip("/")
        key_env = _typed(table, "api_key_env", None, str, path)
        endpoints[name] = Endpoint(name, base_url, key_env)
    return endpoints


def _prices(section: Table, path: Path) -> dict[str, float]:
    return {model: _typed(section, model, 0.0, float, path) for model in section}


def _settings(kind: Any, section: Table, path: Path, name: str) -> Any:
    """A settings dataclass from its section: each value checked against the default's type."""
    defaults = kind()
    known = {item.name: f"default {getattr(defaults, item.name)!r}" for item in fields(kind)}
    _check_keys(section, known, f"{path} [{name}]")
    values: dict[str, Any] = {}
    for key in section:
        default = getattr(defaults, key)
        if isinstance(default, tuple):
            values[key] = _names(section[key], f"{name}.{key}", path)
        elif default is None:
            values[key] = _typed(section, key, None, float, path)
        else:
            values[key] = _typed(section, key, default, type(cast(object, default)), path)
    return kind(**values)
