"""What blame looks at for one missed question: spans, ranks and the probes (design §9.1, §9.4).

Everything here was measured in the run: the chosen pipeline's ranks before and after the reranker, the
hit chunk's rank under dense and BM25 search, the quote embedded alone, the quote's token position, every
measured embedder's rank, near-duplicates and the twin passage. Blame is arithmetic on these.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ragcourt.core.relevance import is_hit
from ragcourt.types import Chunk
from ragcourt.types.questions import Question


@dataclass(frozen=True)
class Facts:
    """One held-out miss of the chosen pipeline, with its probes."""

    question: Question
    chunks: list[Chunk]
    retrieved: tuple[int, ...]
    final: tuple[int, ...]
    k: int
    retriever: str
    reranker: str
    chunk_tokens: list[int]
    quote_tokens: int
    limit: int | None = None
    quote_end_tokens: int | None = None  # tokens from the hit chunk's start to the quote's end
    quote_alone_reaches: bool | None = None  # the quote alone would reach the retrieved depth
    dense_rank: int | None = None  # the hit chunk's rank by dense search with the chosen embedder
    bm25_rank: int | None = None  # its rank by BM25 on the same chunks
    other_embedders: dict[str, int | None] = field(default_factory=dict[str, int | None])
    duplicates: frozenset[int] = frozenset()
    twin_chunks: frozenset[int] = frozenset()
    external: bool = False  # a pipeline of the user's own: ragcourt sees its ranks, not its stages (0006)
    chunks_known: bool = True  # False for such a pipeline when it did not list its chunks

    @property
    def hit(self) -> int | None:
        """The chunk that holds the whole quote (the best ranked one when several do), or None."""
        holders = [chunk.index for chunk in self.chunks if is_hit(chunk, self.question)]
        if not holders:
            return None
        ranked = [index for index in self.final if index in holders]
        return ranked[0] if ranked else holders[0]

    def rank(self, ranked: tuple[int, ...], index: int | None) -> int | None:
        """The 1-based rank of ``index`` in a list, or None."""
        return ranked.index(index) + 1 if index is not None and index in ranked else None

    def uncovered_characters(self) -> int:
        """Visible characters of the quote that lie in no chunk (whitespace between chunks is not lost)."""
        question = self.question
        covered: set[int] = set()
        for chunk in self.chunks:
            if chunk.document == question.document:
                covered |= set(range(max(chunk.start, question.start), min(chunk.end, question.end)))
        visible = [
            offset
            for offset in range(question.start, question.end)
            if not question.quote[offset - question.start].isspace()
        ]
        return sum(1 for offset in visible if offset not in covered)
