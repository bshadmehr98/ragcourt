"""Blame: for every held-out miss, a stage and a mechanism, by code, in a fixed order (design §9.1, D-033).

The checks run stage by stage in the order below; the first that holds is the cause and every later one
that holds is "also seen". A miss always gets exactly one cause: when no check holds, the last resort is
``embedder.meaning`` for a lost chunk (nothing found it) or ``ranking.not_rescued`` for a low one.
Adding a mechanism is one function in its stage's file and its place in that file's list.
"""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame import chunker, embedder, ranking, retriever
from ragcourt.core.blame.facts import Facts

STAGES: list[tuple[str, list[tuple[str, Callable[[Facts], str | None]]]]] = [
    ("chunker", chunker.MECHANISMS),
    ("embedder", embedder.MECHANISMS),
    ("retriever", retriever.MECHANISMS),
    ("ranking", ranking.MECHANISMS),
]


def _names() -> list[str]:
    names: list[str] = []
    for _, mechanisms in STAGES:
        names += [name for name, _ in mechanisms]
    return names


MECHANISM_NAMES = _names()
MEANINGS = {
    "chunker.too_small": "the quote is longer than any chunk",
    "chunker.split": "the quote is cut across a chunk boundary",
    "chunker.dropped": "part of the quote is in no chunk",
    "chunker.over_limit": "the quote lies past the embedder's input limit inside its chunk",
    "chunker.diluted": "the quote alone would be found; inside its long or mixed chunk it is not",
    "embedder.exact_words": "keyword search finds it; the embedder blurs the exact words",
    "embedder.distracted": "a similar passage that does not answer took its place",
    "embedder.meaning": "the embedder does not connect the question to its answer",
    "retriever.keyword_only": "BM25 misses it; dense search finds it",
    "retriever.fusion": "one half of the hybrid search finds it; the fused list does not",
    "retriever.crowded": "near-duplicates fill the retrieved list",
    "ranking.reranker_demoted": "the reranker pushed it out of the top k",
    "ranking.distracted": "the misleading passage ranks above it",
    "ranking.duplicates": "near-duplicates take the top k",
    "ranking.not_rescued": "retrieved below k and nothing lifted it",
}


def mechanisms_holding(facts: Facts) -> list[tuple[str, str]]:
    """Every mechanism that holds, in order, with its evidence."""
    holding: list[tuple[str, str]] = []
    for _, mechanisms in STAGES:
        for name, check in mechanisms:
            evidence = check(facts)
            if evidence is not None:
                holding.append((name, evidence))
    return holding


def cause(facts: Facts) -> tuple[str, str, tuple[str, ...]]:
    """The mechanism that caused the miss, its evidence, and the others also seen."""
    holding = mechanisms_holding(facts)
    if not holding:
        holding = [_last_resort(facts)]
    first, evidence = holding[0]
    return first, evidence, tuple(name for name, _ in holding[1:])


def _last_resort(facts: Facts) -> tuple[str, str]:
    retrieved = facts.rank(facts.retrieved, facts.hit) if facts.hit is not None else None
    if retrieved is not None:
        return "ranking.not_rescued", f"retrieved at rank {retrieved}, below k = {facts.k}"
    return "embedder.meaning", "no stage of this run retrieves the chunk that holds the quote"
