"""``distractor``: a question worded like another passage that does not answer it (design §6.7).

Twins are pairs of windows from different documents with the most content words in common, chosen by code.
The judge confirms the twin does not answer the question.
"""

from __future__ import annotations

from collections import defaultdict

from ragcourt.core.windows import CorpusIndex
from ragcourt.core.words import content_words, jaccard
from ragcourt.types.questions import Offer, Window

NAME = "distractor"
TESTS = "a question worded like another passage that does not answer it"
JUDGE: str | None = "judge.distractor"
MIN_SIMILARITY = 0.12


def offers(index: CorpusIndex) -> list[Offer]:
    """Each window with its most similar window of another document, when they are similar enough."""
    words = [content_words(index.text(window)) for window in index.windows]
    holders: dict[str, list[int]] = defaultdict(list)
    for number, found in enumerate(words):
        for word in found:
            holders[word].append(number)
    result: list[Offer] = []
    for number, window in enumerate(index.windows):
        twin = _twin(number, window, words, holders, index.windows)
        if twin is not None:
            result.append(Offer(window, twin=twin))
    return result


def _twin(
    number: int, window: Window, words: list[set[str]], holders: dict[str, list[int]], windows: list[Window]
) -> Window | None:
    candidates: set[int] = set()
    for word in words[number]:
        candidates.update(holders[word])
    scored = [(jaccard(words[number], words[other]), other) for other in sorted(candidates)]
    eligible = [pair for pair in scored if windows[pair[1]].document != window.document]
    best = max(eligible, default=(0.0, -1), key=lambda pair: (pair[0], -pair[1]))
    return windows[best[1]] if best[0] >= MIN_SIMILARITY else None


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless the question shares as many words (two or more) with the twin as with its own passage."""
    if offer.twin is None:
        return "no twin passage"
    asked = content_words(question)
    with_twin = len(asked & content_words(index.text(offer.twin)))
    with_own = len(asked & content_words(index.text(offer.window)))
    if with_twin < max(with_own, 2):
        counts = f"{with_twin} words with the twin, {with_own} with its own passage"
        return f"shares {counts}: it must lean to the twin"  # the judge then checks the twin does not answer
    return None
