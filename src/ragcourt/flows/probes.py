"""The probes blame needs, measured for the chosen pipeline's held-out misses (design §9.4).

The quote embedded alone, BM25's and dense search's rank of the chunk that holds the quote, the quote's
token position in a chunk longer than the embedder reads, every measured embedder's rank, near-duplicates
and the twin passage. All cheap, all through the cache; used for diagnosis, never in a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ragcourt import stages
from ragcourt.core.audit import duplicate_near
from ragcourt.core.blame.facts import Facts
from ragcourt.core.relevance import is_hit
from ragcourt.flows.evaluate import Evaluator
from ragcourt.stages.retrievers.dense import dot, unit
from ragcourt.text_units import estimate_tokens
from ragcourt.types import Chunk, Search
from ragcourt.types.audit import AuditContext
from ragcourt.types.questions import Question
from ragcourt.types.results import Evaluation, PipelineSpec, QuestionResult


@dataclass
class Prober:
    """Probes for one chosen pipeline; it keeps the searches it built."""

    evaluator: Evaluator
    chosen: PipelineSpec
    step_one: list[Evaluation]
    searches: dict[str, Search] = field(default_factory=dict[str, Search])

    def chunks(self) -> list[Chunk]:
        """The chosen chunking."""
        return self.evaluator.chunked(self.chosen.chunker).chunks

    def facts(self, question: Question, result: QuestionResult, duplicates: frozenset[int]) -> Facts:
        """Everything blame looks at for one miss."""
        chunks = self.chunks()
        sizes = self._sizes()
        hit = _hit(chunks, result, question)
        return Facts(
            question=question,
            chunks=chunks,
            retrieved=result.retrieved,
            final=result.final,
            k=self.evaluator.settings.k,
            retriever=self.chosen.retriever.split(":", maxsplit=1)[0],
            reranker=self.chosen.reranker.split(":", maxsplit=1)[0],
            chunk_tokens=sizes,
            quote_tokens=self._count(question.quote),
            limit=self._limit(),
            quote_end_tokens=self._quote_end(chunks, hit, question, sizes),
            quote_alone_reaches=self._quote_alone(question),
            dense_rank=self._rank("dense", question, hit),
            bm25_rank=self._rank("bm25", question, hit),
            other_embedders=self._others(question),
            duplicates=duplicates,
            twin_chunks=_twin_chunks(chunks, question),
        )

    def duplicates(self) -> frozenset[int]:
        """Chunks of the chosen chunking that nearly repeat an earlier one (audit ``duplicate.near``)."""
        chunks = self.chunks()
        documents = {document.id: document for document in self.evaluator.corpus.documents}
        settings = self.evaluator.project.config.audit
        context = AuditContext(
            documents, {}, [0] * len(chunks), sizes_measured=False, limit=None, settings=settings
        )
        return frozenset(finding.chunk.index for finding in duplicate_near.find(chunks, context))

    def _sizes(self) -> list[int]:
        if self.chosen.embedder is None:
            return [estimate_tokens(chunk.text) for chunk in self.chunks()]
        _, counts = self.evaluator.chunk_vectors(self.chosen.chunker, self.chosen.embedder)
        return counts or [estimate_tokens(chunk.text) for chunk in self.chunks()]

    def _count(self, text: str) -> int:
        if self.chosen.embedder is None:
            return estimate_tokens(text)
        counts = self.evaluator.embedder(self.chosen.embedder).embed([text]).token_counts
        return counts[0] if counts else estimate_tokens(text)

    def _limit(self) -> int | None:
        return self.evaluator.embedder(self.chosen.embedder).max_tokens if self.chosen.embedder else None

    def _quote_end(
        self, chunks: list[Chunk], hit: int | None, question: Question, sizes: list[int]
    ) -> int | None:
        limit = self._limit()
        if hit is None or limit is None or sizes[hit] < limit:
            return None
        prefix = chunks[hit].text[: question.end - chunks[hit].start]
        return self._count(prefix)

    def _quote_alone(self, question: Question) -> bool | None:
        """True when the quote, embedded alone, scores at least as high as the last retrieved chunk."""
        embedder = self.chosen.embedder
        if embedder is None:
            return None
        query = unit(self.evaluator.query_vector(embedder)(question.question))
        quote = unit(self.evaluator.embedder(embedder).embed([question.quote]).vectors[0])
        ranked = self._search("dense")(question.question, self.evaluator.settings.depth)
        return bool(ranked) and dot(query, quote) >= ranked[-1][1]

    def _search(self, retriever: str) -> Search:
        if retriever not in self.searches:
            chunks = [chunk.text for chunk in self.chunks()]
            embedder = self.chosen.embedder
            vectors = (
                self.evaluator.chunk_vectors(self.chosen.chunker, embedder)[0]
                if embedder and retriever == "dense"
                else None
            )
            embed_query = self.evaluator.query_vector(embedder) if embedder else _nothing
            self.searches[retriever] = stages.find("retriever", retriever).function(
                chunks, vectors, embed_query
            )
        return self.searches[retriever]

    def _rank(self, retriever: str, question: Question, hit: int | None) -> int | None:
        if hit is None or (retriever == "dense" and self.chosen.embedder is None):
            return None
        ranked = [
            index for index, _ in self._search(retriever)(question.question, self.evaluator.settings.depth)
        ]
        return ranked.index(hit) + 1 if hit in ranked else None

    def _others(self, question: Question) -> dict[str, int | None]:
        ranks: dict[str, int | None] = {}
        for evaluation in self.step_one:
            result = evaluation.results.get(question.id)
            reciprocal = result.metrics["mrr"] if result else 0.0
            ranks[evaluation.spec.embedder or "-"] = round(1 / reciprocal) if reciprocal else None
        return ranks


def _hit(chunks: list[Chunk], result: QuestionResult, question: Question) -> int | None:
    holders = [chunk.index for chunk in chunks if is_hit(chunk, question)]
    ranked = [index for index in result.final if index in holders]
    if ranked:
        return ranked[0]
    return holders[0] if holders else None


def _twin_chunks(chunks: list[Chunk], question: Question) -> frozenset[int]:
    twin = question.twin
    if twin is None:
        return frozenset()
    return frozenset(
        c.index for c in chunks if c.document == twin.document and c.start < twin.end and twin.start < c.end
    )


def _nothing(text: str) -> list[float]:
    del text
    return []
