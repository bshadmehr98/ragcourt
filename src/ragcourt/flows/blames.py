"""Blame for every held-out miss of the chosen pipeline, with its fix and evidence level (design §9)."""

from __future__ import annotations

from ragcourt.core.blame import cause
from ragcourt.core.boundaries import mark_boundaries
from ragcourt.core.fixes import fix_for
from ragcourt.flows.evaluate import Evaluator
from ragcourt.flows.probes import Prober
from ragcourt.types import Chunk
from ragcourt.types.questions import Question
from ragcourt.types.results import Blame, Evaluation, PipelineSpec

CONTEXT_CHARS = 300


def blame_misses(
    evaluator: Evaluator, chosen: PipelineSpec, measured: list[Evaluation], held_out: list[Question]
) -> list[Blame]:
    """One blame per held-out question the chosen pipeline missed (no hit in the top k)."""
    evaluation = next(item for item in measured if item.spec == chosen)
    step_one = [item for item in measured if item.spec.retriever == "dense" and item.spec.reranker == "none"]
    prober = Prober(evaluator, chosen, _first_step(step_one))
    duplicates = prober.duplicates()
    blames: list[Blame] = []
    for question in held_out:
        result = evaluation.results[question.id]
        if result.metrics["hit_at_k"] == 1.0:
            continue
        facts = prober.facts(question, result, duplicates)
        mechanism, evidence, also = cause(facts)
        level, fix = fix_for(mechanism, question.id, chosen, measured)
        context = surroundings(evaluator.text_of(question.document), prober.chunks(), question)
        stage = mechanism.split(".", maxsplit=1)[0]
        blames.append(
            Blame(
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
        )
    return blames


def _first_step(candidates: list[Evaluation]) -> list[Evaluation]:
    """The embedder step's evaluations: the same chunker, one per embedder."""
    if not candidates:
        return []
    chunker = candidates[0].spec.chunker
    return [item for item in candidates if item.spec.chunker == chunker]


def surroundings(text: str, chunks: list[Chunk], question: Question) -> str:
    """The quote and some text around it, chunk boundaries marked, the quote between « and »."""
    start, end = max(0, question.start - CONTEXT_CHARS), min(len(text), question.end + CONTEXT_CHARS)
    quote_at = (question.start - start, question.end - start)
    window = text[start : question.start] + "«" + question.quote + "»" + text[question.end : end]
    shifted: list[Chunk] = []
    for chunk in chunks:
        if chunk.document != question.document or chunk.end <= start or chunk.start >= end:
            continue
        first = _shift(max(chunk.start, start) - start, quote_at)
        last = _shift(min(chunk.end, end) - start, quote_at)
        shifted.append(Chunk(chunk.document, chunk.index, first, last, ""))
    return mark_boundaries(window, shifted, {})


def _shift(offset: int, quote_at: tuple[int, int]) -> int:
    """An offset of the window after the two quote marks were put in."""
    if offset <= quote_at[0]:
        return offset
    if offset <= quote_at[1]:
        return offset + 1
    return offset + 2
