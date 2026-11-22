"""``numeric``: a number, default, limit, version or date (design §6.7)."""

from __future__ import annotations

import re

from ragcourt.core.windows import CorpusIndex
from ragcourt.types.questions import Offer

NAME = "numeric"
TESTS = "a number, default, limit, version or date"
JUDGE: str | None = "judge.numeric"
PROSE_PART = re.compile(r"[^\n|`]+")  # a line, cut at table bars and code ticks
LETTER = re.compile(r"[A-Za-z]")
DIGIT = re.compile(r"\b\d")
# A number in figures, or in words, as prose writes small counts.
NUMBER = re.compile(
    r"\d|\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|hundred|thousand|once|twice)\b",
    re.I,
)


def offers(index: CorpusIndex) -> list[Offer]:
    """Windows with a number in a line of prose."""
    return [Offer(window) for window in index.windows if number_in_prose(index.text(window))]


def number_in_prose(text: str) -> bool:
    """A letter, then a number later in the same piece of prose: in linear time, whatever the line length."""
    for part in PROSE_PART.finditer(text):
        letter = LETTER.search(part.group(0))
        if letter and DIGIT.search(part.group(0), letter.end()):
            return True
    return False


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless the quote holds a number."""
    if not NUMBER.search(quote):
        return "the quote of a numeric question must hold a number"
    return None
