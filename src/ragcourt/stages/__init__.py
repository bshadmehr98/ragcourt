"""The stage registry: four decorators, lookup, and loading the user's own stages (design §7.2).

A stage is one function registered under a kind and a name::

    from ragcourt.stages import chunker

    @chunker("by_paragraph")
    def by_paragraph(text: str, min_chars: int = 200) -> list[str]: ...

The built-ins live one per file in ``stages/<kind>s/`` and are found by listing those folders, so adding
one is adding a file. The user's own are every ``.py`` file of their ``ragcourt_stages/`` folder,
imported in sorted order. The registry below is the one piece of module-level state in ragcourt
(CONTRIBUTING.md rule 9): decorators run at import time and need somewhere to put what they register.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from ragcourt.errors import ConfigError, RagCourtError

KINDS = ("chunker", "embedder", "retriever", "reranker")
StageFunction = TypeVar("StageFunction", bound=Callable[..., Any])


@dataclass(frozen=True)
class Stage:
    """One registered stage: its kind, its name, the function, and the file that defined it."""

    kind: str
    name: str
    function: Callable[..., Any]
    file: str


_REGISTRY: dict[str, dict[str, Stage]] = {kind: {} for kind in KINDS}


def register(kind: str, name: str, function: Callable[..., Any]) -> Stage:
    """Register ``function`` as the stage ``kind``/``name``; a name already taken elsewhere is an error."""
    if kind not in KINDS:
        raise ConfigError(f"Unknown stage kind {kind!r}; the kinds are {', '.join(KINDS)}.")
    stage = Stage(kind=kind, name=name, function=function, file=inspect.getfile(function))
    existing = _REGISTRY[kind].get(name)
    if existing and not _same_definition(existing, stage):
        raise ConfigError(
            f"Two {kind}s are named {name!r}: one in {existing.file}, one in {stage.file}. "
            "Rename one of them."
        )
    _REGISTRY[kind][name] = stage
    return stage


def _same_definition(old: Stage, new: Stage) -> bool:
    """True when the same function is registered again, as when its file is imported a second time."""
    return old.file == new.file and old.function.__qualname__ == new.function.__qualname__


def _decorator(kind: str, name: str) -> Callable[[StageFunction], StageFunction]:
    def decorate(function: StageFunction) -> StageFunction:
        register(kind, name, function)
        return function

    return decorate


def chunker(name: str) -> Callable[[StageFunction], StageFunction]:
    """Register a chunker: ``(text, **params) -> list[str]`` (design §7.1)."""
    return _decorator("chunker", name)


def embedder(name: str) -> Callable[[StageFunction], StageFunction]:
    """Register an embedder factory: ``(**params) -> Embedder`` (design §7.1)."""
    return _decorator("embedder", name)


def retriever(name: str) -> Callable[[StageFunction], StageFunction]:
    """Register a retriever: ``(chunks, vectors, embed_query, **params) -> Search`` (design §7.1)."""
    return _decorator("retriever", name)


def reranker(name: str) -> Callable[[StageFunction], StageFunction]:
    """Register a reranker: ``(query, candidates, **params) -> list[float]`` (design §7.1)."""
    return _decorator("reranker", name)


def names(kind: str) -> list[str]:
    """The registered names of one kind, sorted."""
    return sorted(_REGISTRY[kind])


def find(kind: str, name: str) -> Stage:
    """The stage registered as ``kind``/``name``, or an error that lists the names there are."""
    stage = _REGISTRY[kind].get(name)
    if stage is None:
        known = ", ".join(names(kind)) or "none"
        raise ConfigError(
            f"No {kind} is named {name!r}. Known {kind}s: {known}. "
            "Your own stages are loaded from ragcourt_stages/ (or --stages DIR)."
        )
    return stage


def load_builtins() -> None:
    """Import every built-in stage file. Importing twice does nothing."""
    for kind in KINDS:
        package = importlib.import_module(f"ragcourt.stages.{kind}s")
        for module in sorted(pkgutil.iter_modules(package.__path__), key=lambda info: info.name):
            importlib.import_module(f"{package.__name__}.{module.name}")


def load_folder(folder: Path) -> list[Path]:
    """Import every ``.py`` file in the user's stage folder, in sorted order; return the files loaded."""
    if not folder.is_dir():
        raise ConfigError(f"The stage folder {folder} does not exist. Create it or pass --stages DIR.")
    files = sorted(folder.glob("*.py"))
    for path in files:
        _load_file(path)
    return files


def _load_file(path: Path) -> None:
    module_name = f"ragcourt_stages.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ConfigError(f"{path} cannot be imported as Python. Check its name and contents.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except RagCourtError:
        raise  # a duplicate name already says what to do
    except Exception as error:
        raise ConfigError(f"Loading your stage file {path} failed: {error!r}. Fix the file.") from error
