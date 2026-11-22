"""Shared fixtures. The default suite is offline and deterministic: no network and no real model
(CONTRIBUTING.md, "Tests")."""

from __future__ import annotations

import sys
from collections.abc import Iterator

import pytest

from ragcourt import stages


@pytest.fixture
def registry() -> Iterator[None]:
    """Restore the stage registry, and forget the user modules, after a test that registers stages."""
    saved = {kind: dict(entries) for kind, entries in stages._REGISTRY.items()}
    yield
    for kind, entries in saved.items():
        stages._REGISTRY[kind] = entries
    for name in list(sys.modules):
        if name == "ragcourt_stages" or name.startswith("ragcourt_stages."):
            del sys.modules[name]
