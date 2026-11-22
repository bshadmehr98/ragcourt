"""``distractor``: a question worded like another passage that does not answer it (design §6.7).

Twins are pairs of windows from different documents with the most content words in common, chosen by code.
The writer is given the words that only the twin uses; the question must use two of them, so its wording
leans to the twin, and the judge then confirms the twin does not answer it.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from ragcourt.core.windows import CorpusIndex
from ragcourt.core.words import content_words, jaccard, words
from ragcourt.types.questions import Offer, Window

NAME = "distractor"
TESTS = "a question worded like another passage that does not answer it"
JUDGE: str | None = "judge.distractor"
JUDGE_WANTS = False  # the judge is asked whether the other passage answers; it must not
MIN_SIMILARITY = 0.12
MAX_SIMILARITY = 0.5  # more alike is a near-duplicate, which answers the same question
TWIN_WORDS = 8  # how many of the twin's own words the writer is offered
NEEDED = 2  # how many of them the question must use


def offers(index: CorpusIndex) -> list[Offer]:
    """Each window with its most similar window of another document, and the twin's own words."""
    found = [content_words(index.text(window)) for window in index.windows]
    holders: dict[str, list[int]] = defaultdict(list)
    for number, contents in enumerate(found):
        for word in contents:
            holders[word].append(number)
    result: list[Offer] = []
    for number, window in enumerate(index.windows):
        twin = _twin(number, window, found, holders, index.windows)
        if twin is not None:
            result.append(Offer(window, term=", ".join(twin_words(index, window, twin)), twin=twin))
    return result


def twin_words(index: CorpusIndex, window: Window, twin: Window) -> list[str]:
    """The twin's most frequent content words that its partner does not use."""
    own = content_words(index.text(window))
    counts = Counter(word for word in words(index.text(twin)) if word not in own and len(word) > 3)
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:TWIN_WORDS]]


def _twin(
    number: int, window: Window, found: list[set[str]], holders: dict[str, list[int]], windows: list[Window]
) -> Window | None:
    candidates: set[int] = set()
    for word in found[number]:
        candidates.update(holders[word])
    scored = [(jaccard(found[number], found[other]), other) for other in sorted(candidates)]
    eligible = [
        pair for pair in scored if windows[pair[1]].document != window.document and pair[0] <= MAX_SIMILARITY
    ]
    best = max(eligible, default=(0.0, -1), key=lambda pair: (pair[0], -pair[1]))
    return windows[best[1]] if best[0] >= MIN_SIMILARITY else None


def check(question: str, quote: str, offer: Offer, index: CorpusIndex) -> str | None:  # noqa: ARG001
    """Fails unless the question uses two of the twin's own words."""
    if offer.twin is None:
        return "no twin passage"
    offered = {word.strip() for word in (offer.term or "").split(",") if word.strip()}
    used = sorted(offered & set(words(question)))
    if len(used) < NEEDED:
        offered_text = ", ".join(sorted(offered))
        return f"uses {len(used)} of the misleading passage's words ({offered_text}); needs {NEEDED}"
    return None
