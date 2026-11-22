"""A deterministic embedder for tests and examples (design §15.2).

Each text becomes a vector of hashed words and word pairs, so texts that share words are close and the
same text always gives the same vector, on every machine. It has a tokenizer (words and punctuation) and
an input limit, and like a real embedder it reads only the first ``max_tokens`` tokens of a text.
"""

from __future__ import annotations

import hashlib
import itertools
import math
import re
from dataclasses import dataclass

from ragcourt.types import Vector

TOKEN = re.compile(r"\w+|[^\w\s]")
PAIR_WEIGHT = 0.5


def fake_tokens(text: str) -> list[str]:
    """The fake embedder's tokens: words and single punctuation marks, lower-cased."""
    return TOKEN.findall(text.lower())


def _slot(feature: str, dimensions: int) -> tuple[int, float]:
    """Where a feature lands in the vector, and with which sign; stable across runs (no ``hash()``)."""
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    index = int.from_bytes(digest[:4], "big") % dimensions
    sign = 1.0 if digest[4] % 2 else -1.0
    return index, sign


@dataclass(frozen=True)
class FakeEmbedder:
    """Implements the ``Embedder`` protocol with no model and no network."""

    model: str = "fake-embedder"
    max_tokens: int | None = 512
    dimensions: int = 256
    tokenizer: str = "fake: words and punctuation"

    def embed(self, texts: list[str]) -> list[Vector]:
        """One unit-length vector per text (all zeros for a text with no words)."""
        return [self._vector(text) for text in texts]

    def count_tokens(self, texts: list[str]) -> list[int] | None:
        """Each text's length in fake tokens."""
        return [len(fake_tokens(text)) for text in texts]

    def _vector(self, text: str) -> Vector:
        tokens = fake_tokens(text)[: self.max_tokens]
        vector = [0.0] * self.dimensions
        for token in tokens:
            index, sign = _slot(token, self.dimensions)
            vector[index] += sign
        for first, second in itertools.pairwise(tokens):
            index, sign = _slot(f"{first} {second}", self.dimensions)
            vector[index] += sign * PAIR_WEIGHT
        length = math.sqrt(sum(value * value for value in vector))
        if length == 0:
            return vector
        return [value / length for value in vector]
