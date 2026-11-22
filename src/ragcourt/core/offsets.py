"""Finding where each chunk a chunker returned lies in its document (design §4.2, D-010).

A chunker returns strings; the spans are found here, so every chunker is judged on the same offsets. Each
chunk is searched from the previous chunk's start + 1, so overlapping chunks and repeated text map in
reading order: first exactly, then with runs of whitespace treated as equal. A chunk found neither way
makes the chunker invalid for the document.
"""

from __future__ import annotations

import re

from ragcourt.errors import ChunkNotInSource
from ragcourt.types import Chunk, Document


def find_text(text: str, piece: str, start: int = 0) -> tuple[int, int] | None:
    """Where ``piece`` occurs in ``text`` at or after ``start``: exactly, else whitespace-insensitively."""
    exact = text.find(piece, start)
    if exact >= 0:
        return exact, exact + len(piece)
    words = piece.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(word) for word in words)
    match = re.compile(pattern).search(text, start)
    return match.span() if match else None


def chunk_spans(document: Document, pieces: list[str], chunker: str) -> list[Chunk]:
    """The chunks of one document with their spans; empty and whitespace-only pieces are dropped."""
    chunks: list[Chunk] = []
    search_from = 0
    for position, piece in enumerate(pieces):
        if not piece.strip():
            continue
        span = find_text(document.text, piece, search_from)
        if span is None:
            raise ChunkNotInSource(
                f"Chunker {chunker!r} returned chunk {position} of {document.id!r}, which is not in the "
                f"source: {piece[:80]!r}. A chunker must return text from the document, unchanged."
            )
        start, end = span
        chunks.append(Chunk(document.id, len(chunks), start, end, document.text[start:end]))
        search_from = start + 1
    return chunks
