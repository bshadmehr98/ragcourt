"""Passages offered to the question writer: windows cut at paragraph boundaries (design §6.1).

Windows are chosen from the documents by code, never from a chunker's output, so questions do not depend on
any chunker (brief §3).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from ragcourt.types import Document
from ragcourt.types.questions import Window

PARAGRAPH = re.compile(r"\S(?:.*\S)?(?:\n(?!\s*\n).*\S)*", re.MULTILINE)
MIN_CHARS = 200


def windows_of(document: Document, size: int) -> list[Window]:
    """Runs of whole paragraphs of about ``size`` characters; a longer paragraph is a window alone."""
    found: list[Window] = []
    start: int | None = None
    end = 0
    for match in PARAGRAPH.finditer(document.text):
        if start is not None and match.end() - start > size:
            found.append(Window(document.id, start, end))
            start = None
        start = match.start() if start is None else start
        end = match.end()
    if start is not None:
        found.append(Window(document.id, start, end))
    return [window for window in found if window.end - window.start >= MIN_CHARS]


@dataclass(frozen=True)
class CorpusIndex:
    """The texts and windows of a corpus, for the category rules."""

    texts: dict[str, str]
    windows: list[Window]
    counted: dict[str, int] = field(default_factory=dict[str, int])  # remembered answers of documents_with

    def text(self, window: Window) -> str:
        """The text of a window."""
        return self.texts[window.document][window.start : window.end]

    def documents_with(self, term: str) -> int:
        """How many documents contain ``term`` exactly (case kept)."""
        if term not in self.counted:
            self.counted[term] = sum(1 for text in self.texts.values() if term in text)
        return self.counted[term]


def index_corpus(documents: Sequence[Document], size: int) -> CorpusIndex:
    """Every window of every document."""
    found: list[Window] = []
    for document in documents:
        found += windows_of(document, size)
    return CorpusIndex({document.id: document.text for document in documents}, found)
