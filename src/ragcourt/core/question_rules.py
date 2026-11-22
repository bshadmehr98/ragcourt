"""The code rules every question passes before any judge (design §6.2, D-028)."""

from __future__ import annotations

import re

from ragcourt.core.words import content_words, jaccard
from ragcourt.text_units import count_tokens
from ragcourt.types.questions import Question

MIN_QUOTE_WORDS = 6
MAX_QUOTE_TOKENS = 120
MIN_QUESTION_WORDS = 3
CODE_CHARS = re.compile(r"[{}();=<>\[\]$`|]")
MARKDOWN_LINK = re.compile(r"\[([^\]\n]*)\]\([^)\s]*\)")


def rule_problem(question: str, quote: str, category: str) -> str | None:
    """Why a question breaks a code rule, or None."""
    words = quote.split()
    if len(words) < MIN_QUOTE_WORDS:
        return f"the quote has {len(words)} words; at least {MIN_QUOTE_WORDS}"
    prose = MARKDOWN_LINK.sub(r"\1", quote)  # [text](https://…) is prose with a link, not code
    if not re.search(r"[A-Za-z]{3,}", quote) or len(CODE_CHARS.findall(prose)) > len(words) / 2:
        return "the quote is not a sentence (a name or a line of code)"
    if count_tokens(quote) > MAX_QUOTE_TOKENS:
        return f"the quote is longer than {MAX_QUOTE_TOKENS} tokens"
    if category != "keyword" and len(question.split()) < MIN_QUESTION_WORDS:
        return f"the question has fewer than {MIN_QUESTION_WORDS} words"
    return None


def duplicate_of(candidate: Question, kept: list[Question]) -> Question | None:
    """An earlier question whose quote overlaps this one's by more than half, or whose text is nearly it."""
    asked = content_words(candidate.question)
    for earlier in kept:
        if earlier.document == candidate.document and _overlap(candidate, earlier) > 0.5:
            return earlier
        if jaccard(asked, content_words(earlier.question)) >= 0.8:
            return earlier
    return None


def _overlap(first: Question, second: Question) -> float:
    shared = min(first.end, second.end) - max(first.start, second.start)
    shortest = min(first.end - first.start, second.end - second.start)
    return shared / shortest if shared > 0 and shortest > 0 else 0.0
