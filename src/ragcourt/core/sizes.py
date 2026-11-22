"""Chunk sizes and their summary: median, 95th percentile and largest (design §5.2, §8.3)."""

from __future__ import annotations

import math

from ragcourt.types.audit import SizeSummary


def percentile(values: list[int], share: float) -> int:
    """The value at ``share`` (0..1) of the sorted values, nearest rank; 0 for no values."""
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil(share * len(ordered)))
    return ordered[rank - 1]


def summarize(sizes: list[int], *, measured: bool) -> SizeSummary:
    """Median, 95th percentile and largest of ``sizes``."""
    return SizeSummary(percentile(sizes, 0.5), percentile(sizes, 0.95), max(sizes, default=0), measured)
