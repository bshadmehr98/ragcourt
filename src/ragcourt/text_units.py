"""Words, sentences and blocks of a text: the reference units every layer counts in (design §4.3, D-009).

Layer 0, so chunkers (layer 1) and metrics (layer 2) count the same way. The reference tokenization is
words and single punctuation marks, by a regular expression on the source text; it is fixed so token
metrics compare across embedders. The estimate of an embedder's tokens, used when it cannot count, is
characters / 4, and is always labelled ``estimated``.
"""

from __future__ import annotations

import bisect
import math
import re

TOKEN = re.compile(r"\w+|[^\w\s]")
# A sentence ends at . ! or ? (and any closing quotes or brackets) followed by whitespace.
CLOSERS = "\"')]\u201d\u2019"  # straight and curly closing quotes, brackets
SENTENCE_END = re.compile(r"[.!?][" + re.escape(CLOSERS) + r"]*(?=\s)")
SENTENCE_FINAL = set(".!?:;}`*|\u00bb" + CLOSERS)


def token_spans(text: str) -> list[tuple[int, int]]:
    """The ``(start, end)`` of every reference token of ``text``."""
    return [match.span() for match in TOKEN.finditer(text)]


def count_tokens(text: str) -> int:
    """How many reference tokens ``text`` has."""
    return len(TOKEN.findall(text))


def estimate_tokens(text: str) -> int:
    """An embedder's token count estimated from characters (characters / 4, rounded up)."""
    return math.ceil(len(text) / 4)


def tokens_between(token_starts: list[int], start: int, end: int) -> int:
    """How many tokens of a text start in ``[start, end)``, given every token's start, sorted."""
    return bisect.bisect_left(token_starts, end) - bisect.bisect_left(token_starts, start)


def sentence_spans(text: str, start: int = 0, end: int | None = None) -> list[tuple[int, int]]:
    """The sentences of ``text[start:end]`` as spans without surrounding whitespace."""
    stop = len(text) if end is None else end
    spans: list[tuple[int, int]] = []
    begin = start
    for match in SENTENCE_END.finditer(text, start, stop):
        spans.append((begin, match.end()))
        begin = match.end()
    spans.append((begin, stop))
    return [strip_span(text, s, e) for s, e in spans if text[s:e].strip()]


def strip_span(text: str, start: int, end: int) -> tuple[int, int]:
    """The span without the whitespace at either end."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def ends_sentence(text: str) -> bool:
    """True when the last visible character closes a sentence, a clause, a bracket or a quote."""
    stripped = text.rstrip()
    return bool(stripped) and stripped[-1] in SENTENCE_FINAL
