"""Span arithmetic the built-in chunkers share: cutting text to a size and packing pieces together.

Chunkers return strings, but work on ``(start, end)`` spans of the document so that every string they
return is a slice of it (design §4.2). Sizes are in reference tokens (``ragcourt.text_units``, D-043).
"""

from __future__ import annotations

import bisect
import re

from ragcourt.errors import ConfigError
from ragcourt.text_units import sentence_spans, strip_span, token_spans, tokens_between

Span = tuple[int, int]
PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n")


class TokenIndex:
    """Where every reference token of one text starts, for counting tokens in a span quickly."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.spans = token_spans(text)
        self.starts = [start for start, _ in self.spans]

    def count(self, start: int, end: int) -> int:
        """Tokens starting inside ``[start, end)``."""
        return tokens_between(self.starts, start, end)

    def between(self, start: int, end: int) -> list[Span]:
        """The token spans starting inside ``[start, end)``, found by bisection (linear scans made
        chunking quadratic in the document's length)."""
        return self.spans[bisect.bisect_left(self.starts, start) : bisect.bisect_left(self.starts, end)]


def check_size(size: object, overlap: object = 0) -> None:
    """A size of one token or more and an overlap from 0 to below the size, both whole numbers."""
    whole = isinstance(size, int) and isinstance(overlap, int) and not isinstance(size, bool)
    if not whole or size < 1 or overlap < 0 or overlap >= size:  # type: ignore[operator]
        raise ConfigError(
            f"size must be a whole number of tokens from 1, and overlap from 0 to below size "
            f"(got size={size!r}, overlap={overlap!r})."
        )


def split_on(text: str, start: int, end: int, pattern: re.Pattern[str]) -> list[Span]:
    """``text[start:end]`` cut after every match of ``pattern``; the separators stay with the left piece."""
    pieces: list[Span] = []
    begin = start
    for match in pattern.finditer(text, start, end):
        pieces.append((begin, match.end()))
        begin = match.end()
    pieces.append((begin, end))
    return [piece for piece in pieces if piece[1] > piece[0]]


def token_windows(index: TokenIndex, start: int, end: int, size: int, overlap: int = 0) -> list[Span]:
    """Windows of at most ``size`` tokens over ``[start, end)``, each starting ``overlap`` tokens early."""
    inside = [span for span in index.between(start, end) if span[1] <= end]
    step = max(1, size - overlap)
    windows: list[Span] = []
    for first in range(0, len(inside), step):
        last = min(first + size, len(inside)) - 1
        windows.append((inside[first][0], inside[last][1]))
        if last == len(inside) - 1:
            break
    return windows


def split_to_size(index: TokenIndex, start: int, end: int, size: int) -> list[Span]:
    """Pieces of at most ``size`` tokens, cut at paragraphs, then sentences, then lines, then words."""
    if index.count(start, end) <= size:
        return [(start, end)]
    for level in ("paragraphs", "sentences", "lines"):
        pieces = _pieces(index.text, start, end, level)
        if len(pieces) > 1:
            result: list[Span] = []
            for piece_start, piece_end in pieces:
                result += split_to_size(index, piece_start, piece_end, size)
            return result
    return token_windows(index, start, end, size)


def _pieces(text: str, start: int, end: int, level: str) -> list[Span]:
    if level == "paragraphs":
        return split_on(text, start, end, PARAGRAPH_BREAK)
    if level == "sentences":
        return sentence_spans(text, start, end)
    return split_on(text, start, end, re.compile(r"\n"))


def pack(index: TokenIndex, pieces: list[Span], size: int, overlap: int = 0) -> list[Span]:
    """Join neighbouring pieces into chunks of at most ``size`` tokens; each new chunk starts ``overlap``
    tokens before the end of the one before it (never before that chunk's own start)."""
    chunks: list[Span] = []
    current: Span | None = None
    for piece in pieces:
        if current is not None and index.count(current[0], piece[1]) <= size:
            current = (current[0], piece[1])
            continue
        if current is None:
            current = piece
            continue
        chunks.append(current)
        current = (_overlap_start(index, current, piece, (size, overlap)), piece[1])
    if current is not None:
        chunks.append(current)
    return [strip_span(index.text, s, e) for s, e in chunks if index.text[s:e].strip()]


def _overlap_start(index: TokenIndex, previous: Span, piece: Span, limits: tuple[int, int]) -> int:
    """Where the next chunk starts: up to ``overlap`` tokens back into the previous one, within ``size``."""
    size, overlap = limits
    before = [s for s, _ in index.between(previous[0] + 1, piece[0])][-overlap:] if overlap > 0 else []
    # Start on a word, not on the punctuation that closed the previous sentence.
    fitting = [s for s in before if index.count(s, piece[1]) <= size and index.text[s].isalnum()]
    return fitting[0] if fitting else piece[0]


def as_strings(text: str, spans: list[Span]) -> list[str]:
    """The text of each span."""
    return [text[start:end] for start, end in spans]
