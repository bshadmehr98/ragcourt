"""``paraphrase``: the same meaning in different words (design §6.7)."""

from __future__ import annotations

from ragcourt.core.windows import CorpusIndex
from ragcourt.core.words import content_words, jaccard
from ragcourt.types.questions import Offer

NAME = "paraphrase"
TESTS = "the same meaning in different words"
JUDGE: str | None = None
MAX_OVERLAP = 0.15


def offers(index: CorpusIndex) -> list[Offer]:
    """Any window."""
    return [Offer(window) for window in index.windows]


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails when the question shares too many content words with the quote."""
    overlap = jaccard(content_words(question), content_words(quote))
    if overlap >= MAX_OVERLAP:
        return f"shares {overlap:.2f} of its words with the quote (paraphrase needs under {MAX_OVERLAP})"
    return None
