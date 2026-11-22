"""Ceilings: how much each stage costs the chosen pipeline (design §9.2).

The chunker ceiling is the share of questions with no ``chunker`` cause; the retrieval ceiling also removes
``embedder`` and ``retriever`` causes; then Hit@k. They cannot increase, and each gap is the share lost to
that stage.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragcourt.types.questions import Question
from ragcourt.types.results import Blame


@dataclass(frozen=True)
class Ceilings:
    """The three levels for one group of questions, and how many questions it has."""

    questions: int
    chunker: float
    retrieval: float
    hit_at_k: float


def ceilings(questions: list[Question], blames: list[Blame]) -> dict[str, Ceilings]:
    """Ceilings per category and ``overall`` (all questions pooled)."""
    groups: dict[str, list[Question]] = {"overall": list(questions)}
    for question in questions:
        groups.setdefault(question.category, []).append(question)
    stage_of = {blame.question: blame.stage for blame in blames}
    return {name: _levels(members, stage_of) for name, members in groups.items()}


def _levels(members: list[Question], stage_of: dict[str, str]) -> Ceilings:
    total = len(members)
    if not total:
        return Ceilings(0, 0.0, 0.0, 0.0)
    lost = [stage_of.get(question.id) for question in members]
    chunker = lost.count("chunker")
    retrieval = lost.count("embedder") + lost.count("retriever")
    ranking = lost.count("ranking")
    return Ceilings(
        total,
        1 - chunker / total,
        1 - (chunker + retrieval) / total,
        1 - (chunker + retrieval + ranking) / total,
    )
