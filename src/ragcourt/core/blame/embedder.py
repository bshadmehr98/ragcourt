"""Blame stage ``embedder``: the chunk is clean, but the model does not bring it into the top (§9.1)."""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame.facts import Facts


def _lost(facts: Facts) -> bool:
    """A clean chunk exists and dense or hybrid retrieval did not return it."""
    return (
        facts.hit is not None and facts.rank(facts.retrieved, facts.hit) is None and facts.retriever != "bm25"
    )


def exact_words(facts: Facts) -> str | None:
    """Keyword search finds the chunk and the embedder does not: it blurs the exact words."""
    if (
        not _lost(facts)
        or facts.retriever != "dense"
        or facts.bm25_rank is None
        or facts.dense_rank is not None
    ):
        return None
    term = f"; the term {facts.question.term!r}" if facts.question.term else ""
    return f"BM25 ranks the chunk {facts.bm25_rank}; the embedder does not retrieve it{term}"


def distracted(facts: Facts) -> str | None:
    """The twin passage (or chunks of it) fill the ranks above the chunk."""
    above = [index for index in facts.retrieved if index in facts.twin_chunks]
    if not _lost(facts) or not above:
        return None
    rank = facts.retrieved.index(above[0]) + 1
    return f"the misleading passage is retrieved at rank {rank}; the answer is not"


def meaning(facts: Facts) -> str | None:
    """Neither the chunk nor the quote alone is retrieved, and keyword search does not find it either."""
    if not _lost(facts) or facts.quote_alone_reaches or facts.bm25_rank is not None:
        return None
    others = ", ".join(f"{name}: {rank or 'not found'}" for name, rank in facts.other_embedders.items())
    return "the model does not connect the question to its answer" + (
        f" (other embedders: {others})" if others else ""
    )


MECHANISMS: list[tuple[str, Callable[[Facts], str | None]]] = [
    ("embedder.exact_words", exact_words),
    ("embedder.distracted", distracted),
    ("embedder.meaning", meaning),
]
