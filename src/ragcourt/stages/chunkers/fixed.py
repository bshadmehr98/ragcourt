"""The ``fixed`` chunker: windows of a fixed number of tokens, blind to structure (design §7.3)."""

from __future__ import annotations

from ragcourt.stages import chunker
from ragcourt.stages.splitting import TokenIndex, as_strings, token_windows


@chunker("fixed")
def fixed(text: str, size: int = 256, overlap: int = 32) -> list[str]:
    """Windows of ``size`` reference tokens, each starting ``overlap`` tokens before the last one ended."""
    index = TokenIndex(text)
    return as_strings(text, token_windows(index, 0, len(text), size, overlap))
