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
