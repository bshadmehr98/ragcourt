"""The ``recursive`` chunker: paragraphs, sentences, lines, words, packed up to a size (design §7.3)."""

from __future__ import annotations

from ragcourt.stages import chunker
from ragcourt.stages.splitting import TokenIndex, as_strings, pack, split_to_size


@chunker("recursive")
def recursive(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    """Chunks of at most ``size`` reference tokens, cut at the largest natural boundary that fits."""
    index = TokenIndex(text)
    pieces = split_to_size(index, 0, len(text), size)
    return as_strings(text, pack(index, pieces, size, overlap))
