"""Fakes and the bundled corpus, for tests, examples and trying ragcourt without models (design §15.2)."""

from __future__ import annotations

from pathlib import Path

from ragcourt.testing.fake_embedder import FakeEmbedder, fake_tokens
from ragcourt.testing.scripted_model import ScriptedModel


def corpus_path() -> Path:
    """The folder of the bundled corpus: a dozen short documents with a planted case each."""
    return Path(__file__).parent / "corpus"


__all__ = ["FakeEmbedder", "ScriptedModel", "corpus_path", "fake_tokens"]
