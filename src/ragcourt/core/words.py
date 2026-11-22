"""Content words, overlap and negation: what the category checks measure (design §6.7)."""

from __future__ import annotations

import re

WORD = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")
NEGATION = re.compile(
    r"\b(not|never|no|none|without|except|unless|cannot|can't|doesn't|isn't|won't|don't)\b", re.I
)
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "to",
        "in",
        "on",
        "for",
        "and",
        "or",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "it",
        "its",
        "this",
        "that",
        "with",
        "as",
        "by",
        "at",
        "from",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "does",
        "do",
        "did",
        "can",
        "could",
        "should",
        "would",
        "will",
        "not",
        "no",
        "any",
        "all",
        "into",
        "than",
        "then",
        "there",
        "their",
        "your",
        "you",
        "we",
        "they",
        "he",
        "she",
        "i",
        "me",
        "my",
        "our",
        "out",
        "up",
        "about",
        "over",
        "under",
        "via",
        "per",
        "if",
        "so",
        "such",
        "these",
        "those",
        "has",
        "have",
        "had",
        "also",
        "may",
        "might",
        "must",
        "one",
        "two",
        "each",
        "other",
        "more",
        "most",
        "some",
        "only",
        "own",
        "same",
        "just",
        "very",
    }
)


def words(text: str) -> list[str]:
    """The words of a text, lower-cased."""
    return [word.lower().strip(".-") for word in WORD.findall(text)]


def content_words(text: str) -> set[str]:
    """Words that carry meaning: no stop words, at least three characters."""
    return {word for word in words(text) if word not in STOP_WORDS and len(word) > 2}


def jaccard(first: set[str], second: set[str]) -> float:
    """Shared words over all words; 0 for two empty sets."""
    union = first | second
    return len(first & second) / len(union) if union else 0.0


def has_negation(text: str) -> bool:
    """True when the text says not, never, no, without, except, unless, cannot …"""
    return bool(NEGATION.search(text))
