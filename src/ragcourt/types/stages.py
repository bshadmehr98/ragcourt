"""The four stage kinds and their signatures (design §7.1). Protocols and aliases only."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


# A pipeline: a retrieval system of the user's own, (query, depth) -> its chunk texts, best first (0006).
Pipeline = Callable[..., list[str]]


@dataclass(frozen=True)
class Embedded:
    """Vectors for a batch of texts, and each text's length in the model's tokens when it was counted.

    ``token_counts`` is None when the embedder cannot count; sizes are then estimated (design §4.3).
    Counting comes with embedding because that is how Ollama reports it: one count per call (D-041).
    """

    vectors: list[Vector]
    token_counts: list[int] | None


class Embedder(Protocol):
    """An embedding model as the pipeline sees it; a registered embedder is a factory returning one."""

    @property
    def model(self) -> str:
        """The model's identity, used to name its cache (design §10.2)."""
        ...

    @property
    def max_tokens(self) -> int | None:
        """The input limit that is in force, in the model's own tokens, or None when unknown (D-040)."""
        ...

    @property
    def tokenizer(self) -> str:
        """How tokens are counted, in a few words (design §4.3)."""
        ...

    def embed(self, texts: list[str], *, as_query: bool = False) -> Embedded:
        """One vector per text, in order, with the token counts. Never caches: the cache wraps it.

        ``as_query`` says the texts are questions, not chunks, for models that embed the two with
        different prefixes (D-042).
        """
        ...
