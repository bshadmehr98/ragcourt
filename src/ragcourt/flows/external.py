"""A pipeline of the user's own: questioned, scored and blamed as far as spans allow (change 0006).

The user's function is called once per question with the question's text and the depth; what it contacts
is the user's business. Its texts are placed in the documents (``core/external.py``), every metric is
computed on held-out questions like any pipeline's, and each miss gets one cause from spans and ranks.
"""

from __future__ import annotations

import functools
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

from ragcourt import stages
from ragcourt.core.audit import duplicate_near
from ragcourt.core.blame import cause
from ragcourt.core.blame.facts import Facts
from ragcourt.core.chunking import strings_or_none
from ragcourt.core.external import Placed, place_texts
from ragcourt.core.fixes import external_fix
from ragcourt.core.leaderboard import Scoring, board
from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import is_hit
from ragcourt.errors import ConfigError, RagCourtError
from ragcourt.flows.blames import surroundings
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.run_plan import chunks_known
from ragcourt.flows.search_steps import Questions, Say, SearchState
from ragcourt.io import run_files
from ragcourt.io.rank_output import board_text
from ragcourt.io.result_data import board_data
from ragcourt.text_units import count_tokens, estimate_tokens
from ragcourt.types.audit import AuditContext
from ragcourt.types.questions import Question
from ragcourt.types.results import Blame, Costs, Evaluation, PipelineSpec, QuestionResult


@dataclass(frozen=True)
class External:
    """One run of the user's pipeline: its evaluation, its texts placed, whether its chunks are known."""

    name: str
    evaluation: Evaluation
    placed: Placed
    chunks_known: bool

    def note(self) -> str:
        """What could and could not be scored, for under the board."""
        total = len(self.placed.chunks)
        lines = [
            f"{self.placed.scorable} of {total} chunk texts of {self.name} were found in your documents."
        ]
        if self.placed.not_found:
            lines.append(
                f"{len(self.placed.not_found)} are not text of your documents (rewritten, or a title or "
                "summary added): they cannot be scored and count as holding no quote."
            )
        if self.placed.several:
            lines.append(
                f"{len(self.placed.several)} are found in more than one place: their place is unknown, so "
                "they cannot be scored either."
            )
        return "\n".join(lines)

    def data(self) -> dict[str, object]:
        """The same as data, for ``results.json``."""
        return {
            "name": self.name,
            "chunks_known": self.chunks_known,
            "texts": len(self.placed.chunks),
            "not_found": len(self.placed.not_found),
            "several": len(self.placed.several),
        }


def _texts(name: str, what: str, call: Callable[[], object]) -> list[str]:
    """What the user's function returned, as a list of strings; its failure is one message."""
    try:
        returned = call()
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
    search = stages.find("pipeline", name).function
    known = chunks_known(name)
    listing = stages.find("pipeline_chunks", name).function if known else list
    table = {text: index for index, text in enumerate(dict.fromkeys(_texts(name, "for its chunks", listing)))}
    depth = evaluator.settings.depth
    ranked: dict[str, tuple[int, ...]] = {}
    query_ms: list[float] = []
    for question in evaluator.questions:
        begin = time.perf_counter()
        texts = _texts(
            name, f"for the question {question.id}", functools.partial(search, question.question, depth)
        )
        query_ms.append((time.perf_counter() - begin) * 1000)
        indices = [table.setdefault(text, len(table)) for text in dict.fromkeys(texts[:depth])]
        ranked[question.id] = tuple(indices)
    placed = place_texts(list(table), evaluator.corpus.documents)
    if table and not placed.scorable:
        raise ConfigError(
            f"None of the {len(table)} chunk texts of your pipeline {name!r} is text of the documents in "
            "this folder, so nothing can be scored. Return the chunks as they are in the documents."
        )
    results = {
        question.id: _result(question, ranked[question.id], placed, evaluator)
        for question in evaluator.questions
    }
    evaluation = Evaluation(
        PipelineSpec.external(name), results, _costs(results, placed, query_ms, evaluator)
    )
    run_files.save_evaluation(evaluator.folder, evaluation)
    return External(name, evaluation, placed, known)


def _result(
    question: Question, indices: tuple[int, ...], placed: Placed, evaluator: Evaluator
) -> QuestionResult:
    settings = evaluator.settings
    chunks = [placed.chunks[index] for index in indices]
    ranking = Ranking(question, chunks, placed.chunks, settings.k, settings.budget_tokens)
    return QuestionResult(question.id, indices, indices, all_metrics(ranking, evaluator.tokens))


def _costs(
    results: dict[str, QuestionResult], placed: Placed, query_ms: list[float], evaluator: Evaluator
) -> Costs:
    sizes = sorted(estimate_tokens(chunk.text) for chunk in placed.chunks) or [0]
    k = evaluator.settings.k
    words = [count_tokens(chunk.text) for chunk in placed.chunks]
    per_query: list[int] = []
    for result in results.values():
        per_query.append(sum(words[index] for index in result.final[:k]))
    latencies = sorted(query_ms) or [0.0]
    return Costs(
        chunk_tokens_median=sizes[len(sizes) // 2],
        chunk_tokens_p95=sizes[min(len(sizes) - 1, int(0.95 * len(sizes)))],
        tokens_per_query=statistics.fmean(per_query) if per_query else 0.0,
        latency_ms_p50=round(latencies[len(latencies) // 2], 2),
        latency_ms_p95=round(latencies[min(len(latencies) - 1, int(0.95 * len(latencies)))], 2),
        cost_usd=None,  # what the user's own system costs is not known to ragcourt
    )


def blame_external(
    evaluator: Evaluator, external: External, measured: list[Evaluation], held_out: list[Question]
) -> list[Blame]:
    """One blame per held-out question the user's pipeline missed."""
    chunks = external.placed.chunks
    texts = [chunk.text for chunk in chunks]
    keyword = stages.find("retriever", "bm25").function(texts, None, None) if external.chunks_known else None
    documents = {document.id: document for document in evaluator.corpus.documents}
    context = AuditContext(documents, {}, [0] * len(chunks), sizes_measured=False, limit=None)
    duplicates = frozenset(finding.chunk.index for finding in duplicate_near.find(chunks, context))
    sizes = [estimate_tokens(text) for text in texts]
    settings = evaluator.settings
    blames: list[Blame] = []
    for question in held_out:
        result = external.evaluation.results[question.id]
        if result.metrics["hit_at_k"] == 1.0:
            continue
        holders = [chunk.index for chunk in chunks if is_hit(chunk, question)]
        found = [index for index, _ in keyword(question.question, settings.depth)] if keyword else []
        facts = Facts(
            question,
            chunks,
            result.retrieved,
            result.final,
            settings.k,
            "pipeline",
            "none",
            sizes,
            estimate_tokens(question.quote),
            bm25_rank=next((found.index(index) + 1 for index in holders if index in found), None),
            duplicates=duplicates,
            chunks_known=external.chunks_known,
        )
        placed = [chunk for chunk in chunks if chunk.document == question.document]
        context_text = surroundings(evaluator.text_of(question.document), placed, question)
        blames.append(_blame(facts, context_text, measured))
    return blames


def _blame(facts: Facts, context: str, measured: list[Evaluation]) -> Blame:
    question = facts.question
    mechanism, evidence, also = cause(facts)
    level, fix = external_fix(mechanism, question.id, measured)
    stage = mechanism.split(".", maxsplit=1)[0]
    return Blame(
        question.id,
        question.question,
        question.category,
        question.document,
        question.quote,
        context,
        stage,
        mechanism,
        evidence,
        also,
        level,
        fix,
    )


def pipeline_step(
    evaluator: Evaluator, name: str, state: SearchState, scoring: tuple[str, Questions], say: Say
) -> tuple[PipelineSpec, list[Blame], dict[str, object]]:
    """The last step of a run with ``--pipeline``: the user's pipeline on a board beside the search's choice
    (when there was a search), its misses blamed. It is one fixed system: nothing is chosen on dev."""
    metric, split = scoring
    run_files.log_progress(evaluator.folder, {"step": "pipeline", "event": "start"})
    say(f"\nYour pipeline {name}: {len(evaluator.questions)} questions …")
    external = run_external(evaluator, name)
    beside = [item for item in state.measured if item.spec == state.best]
    evaluations = [external.evaluation, *beside]
    minimum = evaluator.project.config.questions.min_held_out
    leaderboard = board("pipeline", evaluations, Scoring(split.held_out, metric, minimum, split.held_draws))
    say(board_text(board_data(leaderboard), None))
    say(external.note())
    blames = blame_external(evaluator, external, state.measured, split.held_out)
    spec = external.evaluation.spec
    state.boards.append(leaderboard)
    state.measured.append(external.evaluation)
    labels = [evaluation.spec.label for evaluation in evaluations]
    state.steps.append({"step": "pipeline", "evaluated": labels, "chosen": spec.label, "tied_on_dev": []})
    run_files.log_progress(evaluator.folder, {"step": "pipeline", "event": "end"})
    found: dict[str, object] = {
        "pipeline": external.data(),
        "search_chosen": state.best.label if state.best else None,
    }
    return spec, blames, found
