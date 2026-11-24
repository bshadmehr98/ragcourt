"""A pipeline of the user's own: questioned and scored like any pipeline (change 0006, design §7.5).

The user's function is called once per question with the question's text and the depth; what it contacts
is the user's business. Its texts are placed in the documents (``core/external.py``) and every metric is
computed like any pipeline's. Its misses are blamed in ``flows/blames.py``.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass

from ragcourt import stages
from ragcourt.core.chunking import strings_or_none
from ragcourt.core.external import Placed, place_texts
from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.pipeline import Settings
from ragcourt.core.relevance import token_map
from ragcourt.core.sizes import percentile
from ragcourt.errors import ConfigError, RagCourtError
from ragcourt.flows.evaluate import Evaluator, latency_at
from ragcourt.flows.run_plan import chunks_known
from ragcourt.io import run_files
from ragcourt.text_units import count_tokens, estimate_tokens
from ragcourt.types import Chunk, Pipeline
from ragcourt.types.questions import Question
from ragcourt.types.results import Costs, Evaluation, PipelineSpec, QuestionResult


@dataclass(frozen=True)
class External:
    """One run of the user's pipeline: its evaluation, its texts placed, whether its chunks are known."""

    name: str
    evaluation: Evaluation
    placed: Placed
    chunks_known: bool


def external_data(external: External) -> dict[str, object]:
    """What was asked and what could be placed, for ``results.json`` and the note under the board."""
    return {
        "name": external.name,
        "chunks_known": external.chunks_known,
        "texts": len(external.placed.chunks),
        "not_found": len(external.placed.not_found),
        "several": len(external.placed.several),
    }


def _texts(name: str, what: str, function: Pipeline, *arguments: object) -> list[str]:
    """What the user's function returned, as a list of strings; its failure is one message."""
    try:
        returned: object = function(*arguments)  # type: ignore[arg-type]
    except RagCourtError:
        raise
    except Exception as error:
        raise ConfigError(f"Your pipeline {name!r} failed {what}: {error!r}.") from error
    texts = strings_or_none(returned)
    if texts is None:
        raise ConfigError(f"Your pipeline {name!r} must return a list of strings {what}.")
    return texts


def run_external(evaluator: Evaluator, name: str) -> External:
    """Ask the pipeline every question, place its texts and measure every metric."""
    search: Pipeline = stages.find("pipeline", name).function
    known = chunks_known(name)
    listed = _texts(name, "for its chunks", stages.find("pipeline_chunks", name).function) if known else []
    table: dict[str, int] = {}  # each distinct text and its number, the listed chunks first
    for text in listed:
        table.setdefault(text, len(table))
    depth = evaluator.settings.depth
    ranked: dict[str, tuple[int, ...]] = {}
    query_ms: list[float] = []
    for question in evaluator.questions:
        begin = time.perf_counter()
        texts = _texts(name, f"for the question {question.id}", search, question.question, depth)
        query_ms.append((time.perf_counter() - begin) * 1000)
        indices: list[int] = []
        for text in dict.fromkeys(texts[:depth]):
            indices.append(table.setdefault(text, len(table)))
        ranked[question.id] = tuple(indices)
    placed = place_texts(list(table), evaluator.corpus.documents)
    if table and not placed.scorable:
        raise ConfigError(
            f"None of the {len(table)} chunk texts of your pipeline {name!r} is text of the documents in "
            "this folder, so nothing can be scored. Return the chunks as they are in the documents."
        )
    # The words of a text with no place are counted too: it takes its share of the budget and of precision.
    documents = {document.id: document.text for document in evaluator.corpus.documents}
    tokens = token_map({**documents, **placed.own_texts()})
    results: dict[str, QuestionResult] = {}
    for question in evaluator.questions:
        ranking = _ranking(question, ranked[question.id], placed, evaluator.settings, listed=known)
        order = ranked[question.id]
        results[question.id] = QuestionResult(question.id, order, order, all_metrics(ranking, tokens))
    costs = _costs(results, placed, query_ms, evaluator.settings.k)
    evaluation = Evaluation(PipelineSpec.external(name), results, costs)
    run_files.save_evaluation(evaluator.folder, evaluation)
    return External(name, evaluation, placed, known)


def _ranking(
    question: Question, indices: tuple[int, ...], placed: Placed, settings: Settings, *, listed: bool
) -> Ranking:
    every = list(placed.chunks)
    if not listed:
        # nDCG's ideal is the best chunks of the chunking; with the chunks not listed it would be the best
        # the pipeline happened to return, so the ideal is a chunk that holds the quote whole.
        every.append(Chunk(question.document, -1, question.start, question.end, question.quote))
    ranked = [placed.chunks[index] for index in indices]
    return Ranking(question, ranked, every, settings.k, settings.budget_tokens)


def _costs(results: dict[str, QuestionResult], placed: Placed, query_ms: list[float], k: int) -> Costs:
    sizes = [estimate_tokens(chunk.text) for chunk in placed.chunks]
    words = [count_tokens(chunk.text) for chunk in placed.chunks]
    per_query: list[int] = []
    for result in results.values():
        per_query.append(sum(words[index] for index in result.final[:k]))
    latencies = sorted(query_ms)
    return Costs(
        chunk_tokens_median=percentile(sizes, 0.5),
        chunk_tokens_p95=percentile(sizes, 0.95),
        tokens_per_query=statistics.fmean(per_query) if per_query else 0.0,
        latency_ms_p50=round(latency_at(latencies, 0.5), 2),
        latency_ms_p95=round(latency_at(latencies, 0.95), 2),
        cost_usd=None,  # what the user's own system costs is not known to ragcourt
    )
