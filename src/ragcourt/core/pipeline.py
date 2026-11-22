"""Running one pipeline over the questions (design §8.1).

The chunks and their vectors are given (embedding is the one step that calls a model and goes through the
cache); everything here is deterministic: retrieve ``depth`` candidates, rerank them if a reranker is set,
keep the order, and measure every metric on each question.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import TokenMap
from ragcourt.types import Chunk, Search, Vector
from ragcourt.types.questions import Question
from ragcourt.types.results import QuestionResult

Rerank = Callable[[str, list[str]], list[float]]


@dataclass(frozen=True)
class Settings:
    """How deep to retrieve, how many chunks count, and the token budget of ``recall_at_budget``."""

    k: int = 5
    depth: int = 50
    budget_tokens: int = 400


Clock = Callable[[], float]  # seconds, from the caller: core reads no clock itself (design §3.1)


@dataclass(frozen=True)
class Timing:
    """How long the index took to build and each question took to answer, in milliseconds."""

    index_ms: int
    query_ms: list[float]


def run_pipeline(
    chunks: list[Chunk],
    search_of: Callable[[list[str], list[Vector] | None], Search],
    vectors: list[Vector] | None,
    rerank: Rerank | None,
    questions: list[Question],
    context: tuple[Settings, TokenMap, Clock],
) -> tuple[dict[str, QuestionResult], Timing]:
    """Every question's retrieved and final chunk indices, with its metrics, and the timing."""
    settings, tokens, clock = context
    started = clock()
    search = search_of([chunk.text for chunk in chunks], vectors)
    index_ms = int((clock() - started) * 1000)
    results: dict[str, QuestionResult] = {}
    query_ms: list[float] = []
    for question in questions:
        begin = clock()
        retrieved = [index for index, _ in search(question.question, settings.depth)]
        final = (
            reorder(retrieved, rerank(question.question, [chunks[i].text for i in retrieved]))
            if rerank
            else retrieved
        )
        query_ms.append((clock() - begin) * 1000)
        ranking = Ranking(
            question, [chunks[index] for index in final], chunks, settings.k, settings.budget_tokens
        )
        results[question.id] = QuestionResult(
            question.id, tuple(retrieved), tuple(final), all_metrics(ranking, tokens)
        )
    return results, Timing(index_ms, query_ms)


def reorder(retrieved: list[int], scores: list[float]) -> list[int]:
    """The candidates sorted by the reranker's scores, ties kept in retrieval order."""
    order = sorted(range(len(retrieved)), key=lambda position: (-scores[position], position))
    return [retrieved[position] for position in order]
