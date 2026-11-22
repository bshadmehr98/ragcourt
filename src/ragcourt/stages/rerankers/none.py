"""The ``none`` reranker: keeps the retriever's order (design §7.3)."""

from __future__ import annotations

from ragcourt.stages import reranker


@reranker("none")
def none(query: str, candidates: list[str]) -> list[float]:  # noqa: ARG001 (the reranker signature)
    """Scores that keep the candidates in the order they came."""
    return [float(len(candidates) - position) for position in range(len(candidates))]
