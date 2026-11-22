"""Leaderboards: per category and overall, with intervals, ties and the smallest difference (§8.4, §6.8).

Every number is from held-out questions. A category with fewer held-out questions than the minimum is
"too few to rank": shown with its count, never folded into the overall mean.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ragcourt.core.stats import (
    Resamples,
    interval,
    overall_interval,
    paired_difference,
    separable,
    smallest_difference,
)
from ragcourt.types.questions import Question
from ragcourt.types.results import Board, BoardRow, Evaluation, Interval


@dataclass(frozen=True)
class Scoring:
    """What a board is scored on: which questions, which metric, the minimum per category, the resamples."""

    questions: list[Question]
    metric: str
    min_per_category: int
    draws: dict[str, Resamples]


def by_category(questions: list[Question]) -> dict[str, list[Question]]:
    """Questions grouped by category, each group in id order, the groups in name order."""
    groups: dict[str, list[Question]] = {}
    for question in sorted(questions, key=lambda item: item.id):
        groups.setdefault(question.category, []).append(question)
    return dict(sorted(groups.items()))


def ranked_categories(questions: list[Question], minimum: int) -> tuple[list[str], dict[str, int]]:
    """The categories that can be ranked, and those that are too few with their counts.

    When none reaches the minimum, all are used for the overall (and every one is still reported too few).
    """
    groups = by_category(questions)
    ok = [name for name, members in groups.items() if len(members) >= minimum]
    too_few = {name: len(members) for name, members in groups.items() if len(members) < minimum}
    return (ok or list(groups)), too_few


def values(evaluation: Evaluation, members: Sequence[Question], metric: str) -> list[float]:
    """The metric of each question, in order."""
    return [evaluation.results[question.id].metrics[metric] for question in members]


def board(stage: str, evaluations: list[Evaluation], scoring: Scoring) -> Board:
    """A leaderboard of ``evaluations``: best first (ties in listing order), the winner or the tie."""
    groups = by_category(scoring.questions)
    ranked, too_few = ranked_categories(scoring.questions, scoring.min_per_category)
    table: dict[int, dict[str, list[float]]] = {}
    for evaluation in evaluations:
        table[id(evaluation)] = {
            name: values(evaluation, members, scoring.metric) for name, members in groups.items()
        }
    rows = [_row(e, table[id(e)], ranked, scoring.draws) for e in evaluations]
    order = sorted(range(len(rows)), key=lambda number: (-rows[number].overall.mean, number))
    rows = [rows[number] for number in order]
    ordered = [evaluations[number] for number in order]
    tied = _tied(ordered, table, ranked, scoring.draws)
    rows = [
        BoardRow(row.spec, row.overall, row.categories, tied_with_top=number in tied)
        for number, row in enumerate(rows)
    ]
    winner = rows[0].spec if rows and (len(rows) == 1 or 1 not in tied) else None
    smallest = _smallest(ordered, table, groups, scoring.draws)
    leaders = _leaders(rows, ordered, table, ranked, scoring.draws)
    return Board(stage, scoring.metric, rows, winner, smallest, too_few, leaders)


def _row(
    evaluation: Evaluation, table: dict[str, list[float]], ranked: list[str], draws: dict[str, Resamples]
) -> BoardRow:
    categories = {name: interval(table[name], draws[name]) for name in table}
    overall = overall_interval({name: table[name] for name in ranked}, draws)
    return BoardRow(evaluation.spec, overall, categories)


def _tied(
    ordered: list[Evaluation],
    table: dict[int, dict[str, list[float]]],
    ranked: list[str],
    draws: dict[str, Resamples],
) -> set[int]:
    """Positions (after the top) whose paired difference with the top contains 0."""
    if not ordered:
        return set()
    top = {name: table[id(ordered[0])][name] for name in ranked}
    tied: set[int] = set()
    for number, evaluation in enumerate(ordered[1:], start=1):
        other = {name: table[id(evaluation)][name] for name in ranked}
        if not separable(paired_difference(top, other, draws)):
            tied.add(number)
    return tied


def _smallest(
    ordered: list[Evaluation],
    table: dict[int, dict[str, list[float]]],
    groups: dict[str, list[Question]],
    draws: dict[str, Resamples],
) -> dict[str, float]:
    if len(ordered) < 2:
        return {}
    first, second = table[id(ordered[0])], table[id(ordered[1])]
    return {
        name: smallest_difference(paired_difference({name: first[name]}, {name: second[name]}, draws))
        for name in groups
    }


def _leaders(
    rows: list[BoardRow],
    ordered: list[Evaluation],
    table: dict[int, dict[str, list[float]]],
    ranked: list[str],
    draws: dict[str, Resamples],
) -> dict[str, str]:
    """Categories where another entry beats the overall top, separably."""
    leaders: dict[str, str] = {}
    if len(ordered) < 2:
        return leaders
    for name in ranked:
        best = max(range(len(rows)), key=lambda number: (rows[number].categories[name].mean, -number))
        if best == 0:
            continue
        difference = paired_difference(
            {name: table[id(ordered[best])][name]}, {name: table[id(ordered[0])][name]}, draws
        )
        if separable(difference):
            leaders[name] = rows[best].spec.label
    return leaders


def empty_interval() -> Interval:
    """An interval for nothing measured."""
    return Interval(0.0, 0.0, 0.0)
