"""The ``sentence`` chunker: whole sentences packed up to a size (design §7.3)."""

from __future__ import annotations

from ragcourt.stages import chunker
from ragcourt.stages.splitting import PARAGRAPH_BREAK, TokenIndex, as_strings, pack, split_on
from ragcourt.text_units import sentence_spans


@chunker("sentence")
def sentence(text: str, size: int = 256) -> list[str]:
    """Sentences (never cut, so one long sentence may pass ``size``) packed up to ``size`` tokens."""
    index = TokenIndex(text)
    pieces: list[tuple[int, int]] = []
    for start, end in split_on(text, 0, len(text), PARAGRAPH_BREAK):
        pieces += sentence_spans(text, start, end)
    return as_strings(text, pack(index, pieces, size))
