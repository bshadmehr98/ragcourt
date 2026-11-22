"""The ``dense`` retriever: cosine similarity, exact, in memory (design §7.3).

The search is exact (no approximate index in 0.1), so a chunk is never lost to approximation (design §9.1).
Ties in score are broken by chunk index, so results are deterministic.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from ragcourt.errors import ConfigError
from ragcourt.stages import retriever
from ragcourt.types import Search, Vector


def unit(vector: Vector) -> Vector:
    """The vector scaled to length 1 (a zero vector stays zero)."""
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector] if length else vector


def dot(first: Vector, second: Vector) -> float:
    """The dot product of two vectors."""
    return sum(a * b for a, b in zip(first, second, strict=False))


def top(scores: list[float], depth: int) -> list[tuple[int, float]]:
    """The ``depth`` best (index, score) pairs, best first, ties by index."""
    order = sorted(range(len(scores)), key=lambda index: (-scores[index], index))
    return [(index, scores[index]) for index in order[:depth]]


@retriever("dense")
def dense(chunks: list[str], vectors: list[Vector] | None, embed_query: Callable[[str], Vector]) -> Search:
    """Rank chunks by cosine similarity of their vectors to the question's."""
    if vectors is None:
        raise ConfigError("The dense retriever needs an embedder.")
    normalized = [unit(vector) for vector in vectors]
    del chunks

    def search(query: str, depth: int) -> list[tuple[int, float]]:
        question = unit(embed_query(query))
        scores = [dot(question, vector) for vector in normalized]
        return top(scores, depth)

    return search
