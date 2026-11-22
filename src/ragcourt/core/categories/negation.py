"""``negation``: what is not done, never allowed, or the exception (design §6.7)."""

from __future__ import annotations

from ragcourt.core.windows import CorpusIndex
from ragcourt.core.words import has_negation
from ragcourt.types.questions import Offer

NAME = "negation"
TESTS = "what is not done, never allowed, or the exception"
JUDGE: str | None = "judge.negation"


def offers(index: CorpusIndex) -> list[Offer]:
    """Windows with a negation or an exception in the text."""
    return [Offer(window) for window in index.windows if has_negation(index.text(window))]


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless both the question and the quote hold a negation."""
    if not has_negation(question) or not has_negation(quote):
        return "a negation question and its quote must both say not, never, no, without, except …"
    return None
