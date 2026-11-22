"""``exact_term``: a rare identifier, name or number with its unit, which embedders blur (design §6.7).

The term is chosen by code: found in one document only, and shaped like an identifier (``max_inflight``,
``HMAC-SHA256``, ``--drain-timeout``), an all-capitals name, or a number with a unit (``300 seconds``).
"""

from __future__ import annotations

import re

from ragcourt.core.windows import CorpusIndex
from ragcourt.types.questions import Offer

NAME = "exact_term"
TESTS = "a rare identifier, name or number with its unit"
JUDGE: str | None = None
# Starts only where a word starts, and never gives back letters: linear time on very long words.
IDENTIFIER = r"(?<![A-Za-z0-9])-{0,2}[A-Za-z][A-Za-z0-9]*+(?:[_\-.:/][A-Za-z0-9]++)+"
CAPITALS = r"\b[A-Z][A-Z0-9]{2,}\b"
WITH_UNIT = r"\b\d+(?:\.\d+)?\s?(?:ms|s|seconds|minutes|hours|days|MB|GB|KB|%|percent|tokens|bytes)\b"
TERM = re.compile(f"{IDENTIFIER}|{CAPITALS}|{WITH_UNIT}")


def term_of(text: str, index: CorpusIndex) -> str | None:
    """The best term of a window: in one document only, then longest, then first alphabetically."""
    candidates = {match.group(0).strip(".:/") for match in TERM.finditer(text)}
    rare = [term for term in candidates if len(term) > 3 and index.documents_with(term) == 1]
    return min(rare, key=lambda term: (-len(term), term)) if rare else None


def offers(index: CorpusIndex) -> list[Offer]:
    """Windows that hold a rare term, with the term."""
    found: list[Offer] = []
    for window in index.windows:
        term = term_of(index.text(window), index)
        if term:
            found.append(Offer(window, term=term))
    return found


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless the term is in both the question and the quote."""
    term = (offer.term or "").casefold()
    if term not in question.casefold() or term not in quote.casefold():
        return f"the term {offer.term!r} must be in both the question and the quote"
    return None
