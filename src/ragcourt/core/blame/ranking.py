"""Blame stage ``ranking``: the chunk was retrieved, but ended below k (design §9.1)."""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame.facts import Facts


def _below_k(facts: Facts) -> int | None:
    """The chunk's final rank when it was retrieved but is not in the top k."""
    before = facts.rank(facts.retrieved, facts.hit)
    after = facts.rank(facts.final, facts.hit)
    return after if before is not None and after is not None and after > facts.k else None


def reranker_demoted(facts: Facts) -> str | None:
    """The chunk was in the top k before the reranker, which pushed it out."""
    after = _below_k(facts)
    before = facts.rank(facts.retrieved, facts.hit)
    if after is None or facts.reranker == "none" or before is None or before > facts.k:
        return None
    return f"rank {before} before the reranker, {after} after it"


def distracted(facts: Facts) -> str | None:
    """The chunks above it include the misleading twin passage."""
    after = _below_k(facts)
    above = [index for index in facts.final[: (after or 1) - 1] if index in facts.twin_chunks]
    if after is None or not above:
        return None
    return f"the misleading passage is at rank {facts.final.index(above[0]) + 1}; the answer at {after}"


def duplicates(facts: Facts) -> str | None:
    """The k slots are taken by near-duplicates of one another."""
    after = _below_k(facts)
    taken = [index for index in facts.final[: facts.k] if index in facts.duplicates]
    if after is None or len(taken) * 2 <= facts.k:
        return None
    return f"{len(taken)} of the top {facts.k} are near-duplicates; the answer is at rank {after}"


def not_rescued(facts: Facts) -> str | None:
    """It was below k before reranking and stayed there (or there is no reranker)."""
    after = _below_k(facts)
    if after is None:
        return None
    before = facts.rank(facts.retrieved, facts.hit)
    if facts.retriever == "pipeline":
        return f"your pipeline returns it at rank {after}, below k = {facts.k}"
    if facts.reranker == "none":
        return f"retrieved at rank {after}, below k = {facts.k}; no reranker"
    return f"rank {before} before the reranker, {after} after it"


MECHANISMS: list[tuple[str, Callable[[Facts], str | None]]] = [
    ("ranking.reranker_demoted", reranker_demoted),
    ("ranking.distracted", distracted),
    ("ranking.duplicates", duplicates),
    ("ranking.not_rescued", not_rescued),
]
