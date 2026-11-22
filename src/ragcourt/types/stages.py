"""The four stage kinds and their signatures (design §7.1). Protocols and aliases only."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

Vector = list[float]

# A chunker: the document's text (plus keyword parameters) -> the chunk strings, in order.
Chunker = Callable[..., list[str]]

# What a retriever builds: (query, depth) -> up to ``depth`` (chunk index, score) pairs, best first.
Search = Callable[[str, int], list[tuple[int, float]]]

# A retriever: (chunk texts, their vectors or None, a function embedding the query) -> a Search.
Retriever = Callable[..., Search]

# A reranker: (query, candidate texts) -> one score per candidate; the pipeline sorts.
Reranker = Callable[..., list[float]]


class Embedder(Protocol):
    """An embedding model as the pipeline sees it; a registered embedder is a factory returning one."""

    @property
    def model(self) -> str:
        """The model's identity, used to name its cache (design §10.2)."""
        ...

    @property
    def max_tokens(self) -> int | None:
        """The input limit in the model's own tokens, or None when unknown."""
        ...

    @property
    def tokenizer(self) -> str:
        """How tokens are counted, in a few words (design §4.3)."""
        ...

    def embed(self, texts: list[str]) -> list[Vector]:
        """One vector per text, in order. Never caches: the cache wraps the embedder."""
        ...

    def count_tokens(self, texts: list[str]) -> list[int] | None:
        """Each text's length in the model's tokens (measured), or None when they cannot be counted."""
        ...
