"""Shared fixtures. The default suite is offline and deterministic: no network and no real model
(CONTRIBUTING.md, "Tests")."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from ragcourt import stages


@pytest.fixture
def registry() -> Iterator[None]:
    """Restore the stage registry after a test that registers stages of its own."""
    saved = {kind: dict(entries) for kind, entries in stages._REGISTRY.items()}
    yield
    for kind, entries in saved.items():
        stages._REGISTRY[kind] = entries
