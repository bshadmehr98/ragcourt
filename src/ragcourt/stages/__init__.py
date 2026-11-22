"""The stage registry: four decorators and lookup by kind and name (design §7.2).

A stage is one function registered under a kind and a name::

    from ragcourt.stages import chunker

    @chunker("by_paragraph")
    def by_paragraph(text: str, min_chars: int = 200) -> list[str]: ...

Loading the built-ins and the user's ``ragcourt_stages/`` folder is in ``stages/loader.py``. The registry
below is the one piece of module-level state in ragcourt (CONTRIBUTING.md rule 9): decorators run at
import time and need somewhere to put what they register.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from ragcourt.errors import ConfigError
from ragcourt.stages.loader import load_builtins, load_folder

KINDS = ("chunker", "embedder", "retriever", "reranker")
# Names appear in specs such as ``recursive:size=512``, so ``:``, ``,``, ``=`` and spaces are not allowed.
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")
StageFunction = TypeVar("StageFunction", bound=Callable[..., Any])


@dataclass(frozen=True)
class Stage:
    """One registered stage: its kind, its name, the function, and where it is defined."""

    kind: str
    name: str
    function: Callable[..., Any]
    file: str
    line: int


_REGISTRY: dict[str, dict[str, Stage]] = {kind: {} for kind in KINDS}


def register(kind: str, name: str, function: Callable[..., Any]) -> Stage:
    """Register ``function`` as the stage ``kind``/``name``; a name already taken elsewhere is an error."""
    _check_kind(kind)
    if not NAME.fullmatch(name):
        raise ConfigError(f"{name!r} cannot name a {kind}: use letters, digits, '_', '.' and '-'.")
    code = getattr(function, "__code__", None)
    if code is None:
        raise ConfigError(
            f"{function!r} is not a function; register a function (def) as the {kind} {name!r}."
        )
    stage = Stage(kind, name, function, file=code.co_filename, line=code.co_firstlineno)
    existing = _REGISTRY[kind].get(name)
    if existing and (existing.file, existing.line) != (stage.file, stage.line):
        raise ConfigError(
            f"Two {kind}s are named {name!r}: one in {existing.file}:{existing.line}, "
            f"one in {stage.file}:{stage.line}. Rename one of them."
        )
    _REGISTRY[kind][name] = stage  # the same definition again (its file imported twice) replaces itself
    return stage


def _check_kind(kind: str) -> None:
    if kind not in KINDS:
        raise ConfigError(f"Unknown stage kind {kind!r}; the kinds are {', '.join(KINDS)}.")


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
    _check_kind(kind)
    return sorted(_REGISTRY[kind])


def find(kind: str, name: str) -> Stage:
    """The stage registered as ``kind``/``name``, or an error that lists the names there are."""
    _check_kind(kind)
    stage = _REGISTRY[kind].get(name)
    if stage is None:
        known = ", ".join(names(kind)) or "none"
        raise ConfigError(
            f"No {kind} is named {name!r}. Known {kind}s: {known}. "
            "Your own stages are loaded from ragcourt_stages/ (or --stages DIR)."
        )
    return stage


__all__ = [
    "KINDS",
    "Stage",
    "chunker",
    "embedder",
    "find",
    "load_builtins",
    "load_folder",
    "names",
    "register",
    "reranker",
    "retriever",
]
