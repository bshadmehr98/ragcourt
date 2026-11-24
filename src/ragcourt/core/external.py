"""Where the chunk texts of a pipeline ragcourt did not build lie in the documents (change 0006, §4.2).

A text is placed when it is found in exactly one place of the corpus: exactly, else with runs of whitespace
treated as equal. A text that is not found (the system rewrote it, or added a title) or that is found in
several places cannot be scored: it keeps its rank, holds no quote and covers no tokens, and is counted.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ragcourt.core.offsets import find_text
from ragcourt.types.documents import Chunk, Document

NOWHERE = ""  # the document of a chunk that could not be placed: no question has it


@dataclass(frozen=True)
class Placed:
    """Every distinct text as a chunk, in the order given, and the indices that could not be placed."""

    chunks: list[Chunk]
    not_found: frozenset[int]
    several: frozenset[int]

    @property
    def scorable(self) -> int:
        """How many texts have a place in the documents."""
        return len(self.chunks) - len(self.not_found) - len(self.several)


def places(text: str, documents: Sequence[Document]) -> list[tuple[str, int, int]]:
    """Up to two places ``(document, start, end)`` where ``text`` is found: two means "several"."""
    found: list[tuple[str, int, int]] = []
    for document in documents:
        start = 0
        while len(found) < 2:
            span = find_text(document.text, text, start)
            if span is None:
                break
            found.append((document.id, span[0], span[1]))
            start = span[0] + 1
    return found


def place_texts(texts: Sequence[str], documents: Sequence[Document]) -> Placed:
    """Each text as a chunk at its one place, or nowhere."""
    chunks: list[Chunk] = []
    not_found: set[int] = set()
    several: set[int] = set()
    for index, text in enumerate(texts):
        found = places(text, documents) if text.strip() else []
        if len(found) == 1:
            document, start, end = found[0]
            chunks.append(Chunk(document, index, start, end, text))
            continue
        (several if found else not_found).add(index)
        chunks.append(Chunk(NOWHERE, index, 0, 0, text))
    return Placed(chunks, frozenset(not_found), frozenset(several))
