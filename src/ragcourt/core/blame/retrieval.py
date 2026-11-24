"""Blame stage ``retrieval``: a pipeline of the user's own does not return the chunk (change 0006, §9.1).

ragcourt cannot look inside a system it did not build, so it does not say whether the embedder or the search
method lost the chunk: it says the chunk was not returned, and what it can see from outside.
"""

from __future__ import annotations

from collections.abc import Callable

from ragcourt.core.blame.facts import Facts


def not_found(facts: Facts) -> str | None:
    """A chunk holds the quote (or the chunks are not known) and the pipeline does not return it."""
    if facts.rank(facts.retrieved, facts.hit) is not None:
        return None
    if facts.hit is None and facts.chunks_known:
        return None  # no chunk holds the quote: the chunker's business
    if not facts.chunks_known:
        return (
            f"none of the {len(facts.retrieved)} chunks returned holds the quote; register "
            "pipeline_chunks to tell a chunker's cut from a retrieval miss"
        )
    keyword = f"; keyword search over your chunks ranks it {facts.bm25_rank}" if facts.bm25_rank else ""
    return f"a chunk holds the quote, and it is not among the {len(facts.retrieved)} returned{keyword}"


MECHANISMS: list[tuple[str, Callable[[Facts], str | None]]] = [("retrieval.not_found", not_found)]
