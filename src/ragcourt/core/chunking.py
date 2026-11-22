"""Running one chunker over a corpus and finding every chunk's span (design §4.2, §8.1)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ragcourt.core.offsets import chunk_spans
from ragcourt.errors import ChunkNotInSource, ConfigError, RagCourtError
from ragcourt.types import Chunk, Document


@dataclass(frozen=True)
class Chunked:
    """The chunks of a corpus by one chunker, and how many empty pieces it returned (dropped)."""

    chunker: str
    chunks: list[Chunk]
    dropped_empty: int


def chunk_corpus(documents: Sequence[Document], chunk: Callable[[str], list[str]], name: str) -> Chunked:
    """Chunk every document with ``chunk`` and find the spans; a chunker that fails names the document."""
    chunks: list[Chunk] = []
    dropped = 0
    for document in documents:
        try:
            returned: object = chunk(document.text)
        except RagCourtError:
            raise
        except Exception as error:
            raise ConfigError(f"Chunker {name!r} failed on {document.id!r}: {error!r}.") from error
        pieces = strings_or_none(returned)
        if pieces is None:
            raise ChunkNotInSource(f"Chunker {name!r} must return a list of strings for {document.id!r}.")
        dropped += sum(1 for piece in pieces if not piece.strip())
        found = chunk_spans(document, pieces, name)
        chunks += [Chunk(c.document, len(chunks) + c.index, c.start, c.end, c.text) for c in found]
    return Chunked(name, chunks, dropped)


def strings_or_none(value: object) -> list[str] | None:
    """``value`` as a list of strings, or None when it is anything else."""
    if not isinstance(value, list):
        return None
    items: list[object] = list(value)  # pyright: ignore[reportUnknownArgumentType]
    texts = [item for item in items if isinstance(item, str)]
    return texts if len(texts) == len(items) else None
