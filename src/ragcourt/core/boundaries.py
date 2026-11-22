"""A document with its chunk boundaries marked inline, so the user sees the cuts (design §5.2).

``⟦12⟧`` marks where chunk 12 starts and ``⟧`` where a chunk ends; a flagged chunk's start names its
checks, ``⟦12 cut.mid_sentence⟧``.
"""

from __future__ import annotations

from ragcourt.types import Chunk


def mark_boundaries(text: str, chunks: list[Chunk], flags: dict[int, list[str]]) -> str:
    """``text`` with a marker at every chunk start and end; ``flags`` maps a chunk index to check codes."""
    marks: list[tuple[int, int, str]] = []  # (offset, order: ends before starts, marker)
    for chunk in chunks:
        codes = " ".join(flags.get(chunk.index, []))
        label = f"{chunk.index} {codes}".strip()
        marks.append((chunk.start, 1, f"⟦{label}⟧"))
        marks.append((chunk.end, 0, "⟧"))
    marks.sort(key=lambda mark: (mark[0], mark[1]))
    pieces: list[str] = []
    position = 0
    for offset, _, marker in marks:
        pieces.append(text[position:offset])
        pieces.append(marker)
        position = offset
    pieces.append(text[position:])
    return "".join(pieces)
