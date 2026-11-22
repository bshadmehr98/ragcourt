"""Intervals, paired comparisons and ties (design §8.4, D-011).

A 95% interval from a bootstrap over questions (2,000 resamples, fixed seed). Overall is the mean of the
category means, so every category weighs the same; it is resampled within each category. Two entries are
compared on the same questions by a paired bootstrap of the difference: an interval containing 0 is
"no significant difference".
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

from ragcourt.types.results import Interval

Resamples = list[list[int]]


def resamples(size: int, count: int, seed: int | str) -> Resamples:
    """``count`` lists of ``size`` indices drawn with replacement, fixed by the seed (give each category its
    own seed, so categories of the same size are not resampled in step)."""
    generator = random.Random(seed)  # noqa: S311 (a seeded resample, not a secret)
    population = range(size)
    return [generator.choices(population, k=size) for _ in range(count)]


def interval(values: Sequence[float], draws: Resamples) -> Interval:
    """The mean and its 95% bootstrap interval."""
    if not values:
        return Interval(0.0, 0.0, 0.0)
    means = sorted(mean_of(values, draw) for draw in draws)
    return Interval(sum(values) / len(values), _quantile(means, 0.025), _quantile(means, 0.975))


def mean_of(values: Sequence[float], draw: list[int]) -> float:
    """The mean of the values at the drawn indices."""
    return sum(values[index] for index in draw) / len(draw)


def _quantile(ordered: list[float], share: float) -> float:
    position = min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))
    return ordered[position]


def overall_interval(by_category: Mapping[str, Sequence[float]], draws: dict[str, Resamples]) -> Interval:
    """The mean of category means, with an interval from resampling inside each category."""
    names = [name for name, values in by_category.items() if values]
    if not names:
        return Interval(0.0, 0.0, 0.0)
    count = len(draws[names[0]])
    totals = [0.0] * count
    for name in names:
        values = by_category[name]
        for number, draw in enumerate(draws[name]):
            totals[number] += mean_of(values, draw)
    means = sorted(total / len(names) for total in totals)
    point = sum(sum(by_category[name]) / len(by_category[name]) for name in names) / len(names)
    return Interval(point, _quantile(means, 0.025), _quantile(means, 0.975))


def paired_difference(
    first: Mapping[str, Sequence[float]], second: Mapping[str, Sequence[float]], draws: dict[str, Resamples]
) -> Interval:
    """The interval of (first - second), mean of category means, paired on the same questions."""
    differences: dict[str, Sequence[float]] = {}
    for name, values in first.items():
        differences[name] = [a - b for a, b in zip(values, second[name], strict=True)]
    return overall_interval(differences, draws)


def separable(difference: Interval) -> bool:
    """True when the difference's interval does not contain 0."""
    return difference.low > 0 or difference.high < 0


def smallest_difference(difference: Interval) -> float:
    """Half the width of a difference's interval: smaller differences cannot be told apart (§6.8)."""
    return (difference.high - difference.low) / 2
