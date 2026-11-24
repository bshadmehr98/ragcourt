"""Where the chunk texts of a pipeline ragcourt did not build lie in the documents (change 0006, §4.2).

A text is placed when it is found in exactly one place of the corpus: exactly, or, when it is nowhere
exactly, with runs of whitespace treated as equal. A text that is not found (the system rewrote it, or added
a title) or that is found in several places cannot be scored as an answer: it keeps its rank and holds no
quote, but its own words still count, so it takes its share of the token budget and of token precision.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ragcourt.types.documents import Chunk, Document

UNPLACED = "\0not placed:"  # starts the document id of a text with no place: no question has such a document
MANY = 2  # places looked for: two is already "several"


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

    def own_texts(self) -> dict[str, str]:
        """The unplaced texts as documents of their own, so their words can be counted."""
        return {chunk.document: chunk.text for chunk in self.chunks if chunk.document.startswith(UNPLACED)}


def places(text: str, documents: Sequence[Document]) -> list[tuple[str, int, int]]:
    """Up to two places ``(document, start, end)`` where ``text`` is found: two means "several"."""
    exact = _matches(re.compile(re.escape(text)), documents)
    if exact:
        return exact
    words = [re.escape(word) for word in text.split()]
    return _matches(re.compile(r"\s+".join(words)), documents)


def _matches(pattern: re.Pattern[str], documents: Sequence[Document]) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for document in documents:
        start = 0
        while len(found) < MANY:
            match = pattern.search(document.text, start)
            if match is None:
                break
            found.append((document.id, match.start(), match.end()))
            start = match.start() + 1
    return found


def place_texts(texts: Sequence[str], documents: Sequence[Document]) -> Placed:
    """Each text as a chunk at its one place, or as a document of its own when it has none."""
    chunks: list[Chunk] = []
    not_found: set[int] = set()
    several: set[int] = set()
    for index, text in enumerate(texts):
        found = places(text, documents) if text.strip() else []
        if len(found) == 1:
            document, start, end = found[0]
            chunks.append(Chunk(document, index, start, end, text))
            continue
        if found:
            several.add(index)
        else:
            not_found.add(index)
        chunks.append(Chunk(f"{UNPLACED}{index}", index, 0, len(text), text))
    return Placed(chunks, frozenset(not_found), frozenset(several))
