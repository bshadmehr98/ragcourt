"""Documents as loaded from the user's folder (design §2, §4.1). Data only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    """One source file as text. ``id`` is its path relative to the corpus folder, with ``/``."""

    id: str
    text: str


@dataclass(frozen=True)
class Skipped:
    """A file that was not loaded, and why (for example, not valid UTF-8)."""

    path: str
    reason: str


@dataclass(frozen=True)
class Corpus:
    """The documents of one folder, sorted by id, and the files skipped while reading it."""

    documents: tuple[Document, ...]
    skipped: tuple[Skipped, ...]


@dataclass(frozen=True)
class Chunk:
    """One chunk a chunker returned, at the span the pipeline found for it in its document (design §4.2).

    ``text`` is the source text of the span, which may differ in whitespace from what the chunker returned.
    """

    document: str
    index: int
    start: int
    end: int
    text: str
