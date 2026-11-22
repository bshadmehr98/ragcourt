"""The ``bm25`` retriever: Okapi BM25 over lower-cased words, pure Python (design §7.3)."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Callable

from ragcourt.stages import retriever
from ragcourt.types import Search, Vector

WORD = re.compile(r"\w+")


def terms(text: str) -> list[str]:
    """The words BM25 matches on: lower-cased runs of letters, digits and underscores."""
    return WORD.findall(text.lower())


@retriever("bm25")
def bm25(
    chunks: list[str],
    vectors: list[Vector] | None,  # noqa: ARG001 (the retriever signature)
    embed_query: Callable[[str], Vector],  # noqa: ARG001
    k1: float = 1.2,
    b: float = 0.75,
) -> Search:
    """Rank chunks by BM25 score of the question's words."""
    counts = [Counter(terms(chunk)) for chunk in chunks]
    lengths = [sum(count.values()) for count in counts]
    average = sum(lengths) / len(lengths) if lengths else 0.0
    frequency: Counter[str] = Counter()
    for count in counts:
        frequency.update(count.keys())
    total = len(chunks)

    def weight(term: str) -> float:
        return math.log(1 + (total - frequency[term] + 0.5) / (frequency[term] + 0.5))

    def search(query: str, depth: int) -> list[tuple[int, float]]:
        scores = [0.0] * total
        for term in set(terms(query)):
            if not frequency[term]:
                continue
            for index, count in enumerate(counts):
                found = count[term]
                if found:
                    norm = found + k1 * (1 - b + b * lengths[index] / (average or 1.0))
                    scores[index] += weight(term) * found * (k1 + 1) / norm
        matched = [index for index in range(total) if scores[index] > 0]  # no shared word: not retrieved
        order = sorted(matched, key=lambda index: (-scores[index], index))
        return [(index, scores[index]) for index in order[:depth]]

    return search
