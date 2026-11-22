"""Blame stage ``retriever``: the search method, not the vectors (design §9.1)."""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame.facts import Facts


def _lost(facts: Facts) -> bool:
    return facts.hit is not None and facts.rank(facts.retrieved, facts.hit) is None


def keyword_only(facts: Facts) -> str | None:
    """The retriever is BM25, it misses the chunk, and dense search finds it."""
    if facts.retriever != "bm25" or not _lost(facts):
        return None
    finders = [(name, rank) for name, rank in facts.other_embedders.items() if rank is not None]
    if facts.dense_rank is None and not finders:
        return None
    where = (
        f"dense search ranks it {facts.dense_rank}"
        if facts.dense_rank
        else f"dense search with {finders[0][0]} ranks it {finders[0][1]}"
    )
    return f"BM25 does not retrieve the chunk; {where}"


def fusion(facts: Facts) -> str | None:
    """Hybrid: one of its two lists has the chunk, the fused list does not."""
    if facts.retriever != "hybrid" or not _lost(facts):
        return None
    if facts.dense_rank is None and facts.bm25_rank is None:
        return None
    return f"dense rank {facts.dense_rank or '-'}, BM25 rank {facts.bm25_rank or '-'}; lost in the fusion"


def crowded(facts: Facts) -> str | None:
    """More than half of what was retrieved are near-duplicates, and the chunk is not among it."""
    duplicates = [index for index in facts.retrieved if index in facts.duplicates]
    if not _lost(facts) or len(duplicates) * 2 <= len(facts.retrieved):
        return None
    return f"{len(duplicates)} of the {len(facts.retrieved)} retrieved chunks are near-duplicates"


MECHANISMS: list[tuple[str, Callable[[Facts], str | None]]] = [
    ("retriever.keyword_only", keyword_only),
    ("retriever.fusion", fusion),
    ("retriever.crowded", crowded),
]
