"""The greedy search, embedders first (design §10.1, brief §6).

Four steps, each varying one stage with the best of the steps before: embedders (with the default chunker,
``dense`` and no reranker), chunkers, retrievers, rerankers. A step's best is chosen on dev questions by the
mean of the category means; entries the paired bootstrap cannot tell apart from the top are tied, and among
them the cheaper, then the smaller, then the first listed is kept.
"""

from __future__ import annotations

from dataclasses import dataclass

from ragcourt.core.leaderboard import by_category, ranked_categories, values
from ragcourt.core.stats import Resamples, paired_difference, separable
from ragcourt.types.questions import Question
from ragcourt.types.results import Evaluation, PipelineSpec

STEPS = ("embedder", "chunker", "retriever", "reranker")


@dataclass(frozen=True)
class Candidates:
    """What the search may try at each step."""

    embedders: tuple[str, ...]
    chunkers: tuple[str, ...]
    retrievers: tuple[str, ...]
    rerankers: tuple[str, ...]


def step_specs(step: str, best: PipelineSpec | None, candidates: Candidates) -> list[PipelineSpec]:
    """The pipelines one step evaluates."""
    if step == "embedder" or best is None:
        chunker = candidates.chunkers[0]
        return [PipelineSpec(chunker, embedder, "dense", "none") for embedder in candidates.embedders]
    if step == "chunker":
        return [PipelineSpec(chunker, best.embedder, "dense", "none") for chunker in candidates.chunkers]
    if step == "retriever":
        return [
            PipelineSpec(best.chunker, best.embedder, retriever, "none")
            for retriever in candidates.retrievers
        ]
    rerankers = ["none", *[name for name in candidates.rerankers if name != "none"]]
    return [PipelineSpec(best.chunker, best.embedder, best.retriever, reranker) for reranker in rerankers]


@dataclass(frozen=True)
class Choice:
    """The step's chosen pipeline, and the entries tied with it on dev."""

    best: PipelineSpec
    tied: list[PipelineSpec]


def choose(
    evaluations: list[Evaluation], dev: list[Question], metric: str, draws: dict[str, Resamples]
) -> Choice:
    """The best entry on dev; among those tied with the top, the cheaper, then smaller, then first listed."""
    groups = by_category(dev)
    ranked, _ = ranked_categories(dev, 1)
    scores = [_score(evaluation, groups, ranked, metric) for evaluation in evaluations]
    top = max(range(len(evaluations)), key=lambda number: (scores[number], -number))
    tied = [
        number
        for number in range(len(evaluations))
        if number == top or _tied(evaluations, top, number, (groups, ranked, metric, draws))
    ]
    keep = min(tied, key=lambda number: _tie_break(evaluations[number], number))
    return Choice(evaluations[keep].spec, [evaluations[number].spec for number in tied if number != keep])


def _score(
    evaluation: Evaluation, groups: dict[str, list[Question]], ranked: list[str], metric: str
) -> float:
    means = [
        sum(values(evaluation, groups[name], metric)) / len(groups[name]) for name in ranked if groups[name]
    ]
    return sum(means) / len(means) if means else 0.0


def _tied(
    evaluations: list[Evaluation],
    top: int,
    other: int,
    context: tuple[dict[str, list[Question]], list[str], str, dict[str, Resamples]],
) -> bool:
    groups, ranked, metric, draws = context
    first = {name: values(evaluations[top], groups[name], metric) for name in ranked}
    second = {name: values(evaluations[other], groups[name], metric) for name in ranked}
    return not separable(paired_difference(first, second, draws))


def _tie_break(evaluation: Evaluation, listed: int) -> tuple[float, float, int]:
    cost = evaluation.costs.cost_usd if evaluation.costs.cost_usd is not None else float("inf")
    return cost, evaluation.costs.tokens_per_query, listed
