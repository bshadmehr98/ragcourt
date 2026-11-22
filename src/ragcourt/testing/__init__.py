"""Fakes and the bundled corpus, for tests, examples and trying ragcourt without models (design §15.2)."""

from __future__ import annotations

from pathlib import Path

from ragcourt import stages
from ragcourt.testing.fake_embedder import FakeEmbedder, fake_tokens
from ragcourt.testing.fake_endpoint import FakeEndpointState, fake_endpoint
from ragcourt.testing.fake_ollama import FakeOllamaState, fake_ollama
from ragcourt.testing.scripted_model import ScriptedModel
from ragcourt.testing.scripted_replies import ScriptedReplies


def corpus_path() -> Path:
    """The folder of the bundled corpus: thirteen short documents with planted cases (design §15.2)."""
    return Path(__file__).parent / "corpus"


def fake_embedder(max_tokens: int = 512, dimensions: int = 256) -> FakeEmbedder:
    """The ``fake`` embedder stage: deterministic, no model, no network."""
    return FakeEmbedder(max_tokens=max_tokens, dimensions=dimensions)


def register_fakes() -> None:
    """Register the ``fake`` embedder, so ``--embedder fake`` and ``[models] embedders = ["fake"]`` work."""
    stages.register("embedder", "fake", fake_embedder)


from ragcourt.testing.offline import offline_project  # noqa: E402 (needs register_fakes above)

__all__ = [
    "FakeEmbedder",
    "FakeEndpointState",
    "FakeOllamaState",
    "ScriptedModel",
    "ScriptedReplies",
    "corpus_path",
    "fake_embedder",
    "fake_endpoint",
    "fake_ollama",
    "fake_tokens",
    "offline_project",
    "register_fakes",
]
