"""The ``markdown`` chunker: one section per heading, the heading kept, then ``recursive`` inside (§7.3)."""

from __future__ import annotations

import re

from ragcourt.stages import chunker
from ragcourt.stages.splitting import TokenIndex, as_strings, pack, split_to_size

# An ATX heading line (# Title), or a line underlined with === or --- (a setext heading).
HEADING = re.compile(r"^(#{1,6}[ \t].*|[^\n]+\n(=+|-+)[ \t]*)$", re.MULTILINE)


@chunker("markdown")
def markdown(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    """Sections from one heading to the next; a section over ``size`` tokens is cut like ``recursive``."""
    index = TokenIndex(text)
    starts = sorted({0, *(match.start() for match in HEADING.finditer(text))})
    spans: list[tuple[int, int]] = []
    for start, end in zip(starts, [*starts[1:], len(text)], strict=True):
        pieces = split_to_size(index, start, end, size)
        spans += pack(index, pieces, size, overlap)
    return as_strings(text, spans)
