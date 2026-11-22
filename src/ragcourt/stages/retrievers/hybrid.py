"""The ``hybrid`` retriever: reciprocal-rank fusion of dense and BM25 (design §7.3).

Each list contributes ``weight / (k + rank)``; ``k`` is 60 as in the original paper. The two lists are
taken to the same depth as the fused one, so a chunk in either list can be fused.
"""

from __future__ import annotations

from collections.abc import Callable

from ragcourt import stages
from ragcourt.stages import retriever
from ragcourt.types import Search, Vector


def fuse(lists: list[list[tuple[int, float]]], weights: list[float], k: int) -> dict[int, float]:
    """Reciprocal-rank fusion scores of several ranked lists."""
    fused: dict[int, float] = {}
    for ranked, weight in zip(lists, weights, strict=True):
        for rank, (index, _) in enumerate(ranked, start=1):
            fused[index] = fused.get(index, 0.0) + weight / (k + rank)
    return fused


@retriever("hybrid")
def hybrid(
    chunks: list[str],
    vectors: list[Vector] | None,
    embed_query: Callable[[str], Vector],
    k: int = 60,
    dense_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> Search:
    """Fuse the dense and BM25 rankings."""
    dense = stages.find("retriever", "dense").function(chunks, vectors, embed_query)
    keyword = stages.find("retriever", "bm25").function(chunks, vectors, embed_query)

    def search(query: str, depth: int) -> list[tuple[int, float]]:
        fused = fuse([dense(query, depth), keyword(query, depth)], [dense_weight, bm25_weight], k)
        order = sorted(fused, key=lambda index: (-fused[index], index))
        return [(index, fused[index]) for index in order[:depth]]

    return search
