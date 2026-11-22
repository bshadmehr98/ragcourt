"""Blame stage ``chunker``: no chunk holds the whole quote, or the one that does hides it (design §9.1)."""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame.facts import Facts


def too_small(facts: Facts) -> str | None:
    """The quote is longer than the chunker's largest chunk."""
    largest = max(facts.chunk_tokens, default=0)
    if facts.hit is None and facts.quote_tokens > largest:
        return f"the quote has {facts.quote_tokens} tokens; the largest chunk has {largest}"
    return None


def split(facts: Facts) -> str | None:
    """The quote is cut across a chunk boundary."""
    question = facts.question
    if facts.hit is not None or facts.uncovered_characters() > 0:
        return None
    cuts = [
        c for c in facts.chunks if c.document == question.document and question.start < c.end < question.end
    ]
    if not cuts:
        return None
    at = cuts[0].end
    text = question.quote
    cut_at = at - question.start
    before, after = text[max(0, cut_at - 30) : cut_at], text[cut_at : cut_at + 30]
    return f"a chunk ends inside the quote: …{before!r} | {after!r}…"


def dropped(facts: Facts) -> str | None:
    """Part of the quote is in no chunk at all."""
    missing = facts.uncovered_characters()
    if facts.hit is None and missing > 0:
        return f"{missing} characters of the quote are in no chunk"
    return None


def over_limit(facts: Facts) -> str | None:
    """A chunk holds the quote, but the quote lies past the embedder's input limit inside it."""
    if facts.hit is None or facts.limit is None or facts.quote_end_tokens is None:
        return None
    if facts.quote_end_tokens >= facts.limit and facts.retriever != "bm25":
        return (
            f"the quote ends at token {facts.quote_end_tokens} of its chunk; the embedder reads {facts.limit}"
        )
    return None


def diluted(facts: Facts) -> str | None:
    """A chunk holds the quote, the quote alone would be retrieved, the chunk is not: drowned in its chunk."""
    if facts.hit is None or facts.rank(facts.retrieved, facts.hit) is not None or facts.retriever == "bm25":
        return None
    if facts.quote_alone_reaches:
        size = facts.chunk_tokens[facts.hit]
        return f"the quote alone would be retrieved; inside its {size}-token chunk it is not"
    return None


MECHANISMS: list[tuple[str, Callable[[Facts], str | None]]] = [
    ("chunker.too_small", too_small),
    ("chunker.split", split),
    ("chunker.dropped", dropped),
    ("chunker.over_limit", over_limit),
    ("chunker.diluted", diluted),
]
