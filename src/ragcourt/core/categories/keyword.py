"""``keyword``: a few search terms, no sentence (design §6.7)."""

from __future__ import annotations

from ragcourt.core.windows import CorpusIndex
from ragcourt.types.questions import Offer

NAME = "keyword"
TESTS = "a few search terms, no sentence"
JUDGE: str | None = None


def offers(index: CorpusIndex) -> list[Offer]:
    """Any window."""
    return [Offer(window) for window in index.windows]


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless the query has 2 to 6 words and no question mark."""
    count = len(question.split())
    if not 2 <= count <= 6 or "?" in question:
        return f"a keyword search has 2 to 6 words and no question mark ({count} words)"
    return None
