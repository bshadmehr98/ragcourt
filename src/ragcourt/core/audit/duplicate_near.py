"""``duplicate.near``: the chunk is nearly the same as an earlier one (design §5.1, D-044).

Similarity is the Jaccard index of the two chunks' word 5-grams. Candidates are found through the
5-grams they share, so the cost grows with the overlap, not with the square of the number of chunks.
"""

from __future__ import annotations

import re
from collections import defaultdict

from ragcourt.types.audit import AuditContext, Finding
from ragcourt.types.documents import Chunk

CODE = "duplicate.near"
MEANING = "is nearly the same text as an earlier chunk"
WORD = re.compile(r"\w+")
SHINGLE = 5
# A 5-gram in more chunks than this is boilerplate (its own check): later holders are not indexed.
MAX_HOLDERS = 64


def shingles(text: str) -> set[tuple[str, ...]]:
    """The word 5-grams of a text, lower-cased."""
    words = WORD.findall(text.lower())
    return {tuple(words[i : i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)}


def find(chunks: list[Chunk], context: AuditContext) -> list[Finding]:
    """Chunks whose 5-gram Jaccard similarity with an earlier chunk reaches the threshold."""
    seen: dict[tuple[str, ...], list[int]] = defaultdict(list)
    sets: list[set[tuple[str, ...]]] = []
    found: list[Finding] = []
    for number, chunk in enumerate(chunks):
        own = shingles(chunk.text)
        sets.append(own)
        match = _best_earlier(own, seen, sets)
        if match is not None and match[1] >= context.settings.near_duplicate_jaccard:
            earlier = chunks[match[0]]
            detail = f"{match[1]:.2f} similar to chunk {earlier.index} of {earlier.document}"
            found.append(Finding(CODE, chunk, detail))
        for gram in own:
            if len(seen[gram]) < MAX_HOLDERS:
                seen[gram].append(number)
    return found


def _best_earlier(
    own: set[tuple[str, ...]], seen: dict[tuple[str, ...], list[int]], sets: list[set[tuple[str, ...]]]
) -> tuple[int, float] | None:
    shared: dict[int, int] = defaultdict(int)
    for gram in own:
        for earlier in seen.get(gram, ()):
            shared[earlier] += 1
    best: tuple[int, float] | None = None
    for earlier in shared:  # the capped index finds candidates; each is scored exactly
        similarity = len(own & sets[earlier]) / len(own | sets[earlier])
        if best is None or similarity > best[1]:
            best = (earlier, similarity)
    return best
