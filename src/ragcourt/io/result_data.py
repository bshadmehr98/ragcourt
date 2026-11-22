"""Turning boards, evaluations and blames into the plain data of ``results.json`` (design §13.3)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragcourt.types.results import Board, Evaluation, Interval


def interval_data(value: Interval) -> dict[str, float]:
    """A mean and its interval, rounded."""
    return {"mean": round(value.mean, 4), "low": round(value.low, 4), "high": round(value.high, 4)}


def board_data(board: Board) -> dict[str, Any]:
    """A leaderboard as data."""
    rows: list[dict[str, Any]] = []
    for row in board.rows:
        categories = {name: interval_data(value) for name, value in row.categories.items()}
        rows.append(
            {
                "label": row.spec.label,
                "overall": interval_data(row.overall),
                "categories": categories,
                "tied_with_top": row.tied_with_top,
            }
        )
    return {
        "stage": board.stage,
        "metric": board.metric,
        "rows": rows,
        "winner": board.winner.label if board.winner else None,
        "smallest_difference": {name: round(value, 4) for name, value in board.smallest_difference.items()},
        "too_few": board.too_few,
        "category_leaders": board.category_leaders,
    }


def configuration_data(evaluation: Evaluation, held_out: list[str], dev: list[str]) -> dict[str, Any]:
    """One evaluated pipeline: its spec, costs, and mean of every metric on held-out and dev questions."""
    return {
        "label": evaluation.spec.label,
        "spec": asdict(evaluation.spec),
        "costs": asdict(evaluation.costs),
        "held_out": _means(evaluation, held_out),
        "dev": _means(evaluation, dev),
    }


def _means(evaluation: Evaluation, ids: list[str]) -> dict[str, float]:
    if not ids:
        return {}
    means: dict[str, float] = {}
    for name in evaluation.results[ids[0]].metrics:
        total = sum(evaluation.results[key].metrics[name] for key in ids)
        means[name] = round(total / len(ids), 4)
    return means
