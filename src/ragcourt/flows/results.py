"""Assembling ``results.json``: everything ``explain`` and the report read (design §13.3)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragcourt.core.audit import CODES, audit
from ragcourt.core.ceilings import ceilings
from ragcourt.core.plan import Estimate
from ragcourt.core.structure import structure_of
from ragcourt.flows.evaluate import Evaluator
from ragcourt.io.result_data import board_data, configuration_data
from ragcourt.text_units import estimate_tokens
from ragcourt.types.audit import AuditContext
from ragcourt.types.results import Blame, Board, Evaluation, PipelineSpec

Searched = tuple[list[dict[str, object]], list[Board], list[Evaluation]]


def results_data(
    evaluator: Evaluator,
    planned: tuple[dict[str, object], Estimate],
    searched: Searched,
    chosen: PipelineSpec,
    blames: list[Blame],
    minutes: float,
) -> dict[str, Any]:
    """The results of a finished run."""
    plan, guess = planned
    steps, boards, measured = searched
    held_out = [question for question in evaluator.questions if question.split == "held-out"]
    dev_ids = [question.id for question in evaluator.questions if question.split == "dev"]
    held_ids = [question.id for question in held_out]
    unique = {evaluation.spec.label: evaluation for evaluation in measured}
    chosen_evaluation = unique[chosen.label]
    # One chunking embedded by one embedder costs once, however many pipelines share it.
    paid = {(e.spec.chunker, e.spec.embedder): e.costs.cost_usd for e in unique.values() if e.costs.vectors}
    costs = list(paid.values())
    return {
        "complete": True,
        "run": evaluator.folder.name,
        "plan": plan,
        "estimate": {"minutes": round(guess.minutes, 1), **asdict(guess)},
        "questions": _question_counts(evaluator),
        "steps": steps,
        "boards": [board_data(board) for board in boards],
        "configurations": [
            configuration_data(evaluation, held_ids, dev_ids) for evaluation in unique.values()
        ],
        "chosen": chosen.label,
        "chosen_spec": asdict(chosen),
        "ceilings": {name: asdict(value) for name, value in ceilings(held_out, blames).items()},
        "blames": [asdict(blame) for blame in blames],
        "confirmed_share": round(sum(blame.level == "confirmed" for blame in blames) / len(blames), 4)
        if blames
        else None,
        "held_out_ranks": {key: _ranks(chosen_evaluation, key) for key in held_ids},
        "audit": _audit(evaluator, chosen),
        "time_minutes": round(minutes, 2),
        "cost_usd": None if None in costs else round(sum(cost or 0.0 for cost in costs), 6),
    }


def _question_counts(evaluator: Evaluator) -> dict[str, Any]:
    counts: dict[str, dict[str, int]] = {}
    for question in evaluator.questions:
        entry = counts.setdefault(question.category, {"dev": 0, "held-out": 0})
        entry[question.split] = entry.get(question.split, 0) + 1
    minimum = evaluator.project.config.questions.min_held_out
    return {"total": len(evaluator.questions), "by_category": counts, "min_held_out": minimum}


def _ranks(evaluation: Evaluation, key: str) -> dict[str, float]:
    metrics = evaluation.results[key].metrics
    reciprocal = metrics["mrr"]
    return {"first_hit": round(1 / reciprocal) if reciprocal else 0, "hit_at_k": metrics["hit_at_k"]}


def _audit(evaluator: Evaluator, chosen: PipelineSpec) -> dict[str, Any]:
    """The audit of the chosen chunking: how many chunks each check flags (design §13.4)."""
    chunks = evaluator.chunked(chosen.chunker).chunks
    counts: list[int] | None = None
    limit = None
    if chosen.embedder and chosen.retriever != "bm25":
        counts = evaluator.chunk_vectors(chosen.chunker, chosen.embedder)[1]
        limit = evaluator.embedder(chosen.embedder).max_tokens
    sizes = counts or [estimate_tokens(chunk.text) for chunk in chunks]
    documents = {document.id: document for document in evaluator.corpus.documents}
    structures = {name: structure_of(document.text) for name, document in documents.items()}
    context = AuditContext(
        documents, structures, sizes, counts is not None, limit, evaluator.project.config.audit
    )
    found = dict.fromkeys(CODES, 0)
    for finding in audit(chunks, context):
        found[finding.code] += 1
    return {"chunker": chosen.chunker, "chunks": len(chunks), "counts": found}
