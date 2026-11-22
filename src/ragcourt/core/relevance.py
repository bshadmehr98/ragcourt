"""Hits and token coverage: when a chunk answers a question (design §8.2, D-013).

A chunk is a hit when its span, in the quote's document, contains the whole quote. Token measures use the
reference tokens of the source text (design §4.3): a token belongs to a span when it lies inside it.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

from ragcourt.text_units import token_spans
from ragcourt.types import Chunk
from ragcourt.types.questions import Question


def is_hit(chunk: Chunk, question: Question) -> bool:
    """True when the chunk holds the whole quote."""
    return chunk.document == question.document and chunk.start <= question.start and question.end <= chunk.end


@dataclass(frozen=True)
class TokenMap:
    """Every reference token of every document: where each starts and ends."""

    starts: dict[str, list[int]]
    ends: dict[str, list[int]]

    def tokens_in(self, document: str, start: int, end: int) -> set[tuple[str, int]]:
        """The tokens lying inside ``[start, end)`` of ``document``, as ``(document, token number)``."""
        starts, ends = self.starts.get(document, []), self.ends.get(document, [])
        first = bisect.bisect_left(starts, start)
        last = bisect.bisect_right(ends, end)
        return {(document, number) for number in range(first, last)}


def token_map(texts: dict[str, str]) -> TokenMap:
    """The reference tokens of every document."""
    starts: dict[str, list[int]] = {}
    ends: dict[str, list[int]] = {}
    for name, text in texts.items():
        spans = token_spans(text)
        starts[name] = [span[0] for span in spans]
        ends[name] = [span[1] for span in spans]
    return TokenMap(starts, ends)
