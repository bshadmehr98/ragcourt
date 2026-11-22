"""Evaluating one pipeline on every question, with chunkings and vectors shared between pipelines (§8.1).

Chunking costs nothing and is kept in memory; vectors come through the embedding cache (design §10.2), so a
chunker and embedder pair is embedded once per corpus, ever. Each finished evaluation is written to the run's
folder, so a resumed run does not measure it again (design §10.4).
"""

from __future__ import annotations

import functools
import inspect
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ragcourt import stages
from ragcourt.core.chunking import Chunked, chunk_corpus
from ragcourt.core.pipeline import Rerank, Settings, Timing, run_pipeline
from ragcourt.core.relevance import TokenMap
from ragcourt.core.sizes import percentile
from ragcourt.io import run_files
from ragcourt.io.client import ENDPOINT_PREFIX
from ragcourt.io.project import Project
from ragcourt.io.prompts import load_prompt
from ragcourt.stages.specs import check_params, parse_spec
from ragcourt.text_units import count_tokens, estimate_tokens
from ragcourt.types import Chunk, Corpus, Embedder, Search, Vector
from ragcourt.types.questions import Question
from ragcourt.types.results import Costs, Evaluation, PipelineSpec, QuestionResult

RETRIEVER_ARGUMENTS = ("chunks", "vectors", "embed_query")
RERANKER_INJECTED = ("client", "prompt")


@dataclass
class Evaluator:
    """Evaluates pipelines for one run; its state is what it has already chunked, embedded and measured."""

    project: Project
    corpus: Corpus
    questions: list[Question]
    settings: Settings
    tokens: TokenMap
    folder: Path
    chunkings: dict[str, Chunked] = field(default_factory=dict[str, Chunked])
    embedders: dict[str, Embedder] = field(default_factory=dict[str, Embedder])
    vectors: dict[tuple[str, str], tuple[list[Vector], list[int] | None]] = field(
        default_factory=dict[tuple[str, str], tuple[list[Vector], list[int] | None]]
    )
    queries: dict[str, dict[str, Vector]] = field(default_factory=dict[str, dict[str, Vector]])

    def text_of(self, document: str) -> str:
        """A document's text."""
        return next(item.text for item in self.corpus.documents if item.id == document)

    def chunked(self, spec_text: str) -> Chunked:
        """The corpus cut by one chunker (checked parameters, spans found)."""
        if spec_text not in self.chunkings:
            spec = parse_spec(spec_text)
            stage = stages.find("chunker", spec.name)
            check_params(stage.function, spec)
            chunk = functools.partial(stage.function, **spec.kwargs())
            self.chunkings[spec_text] = chunk_corpus(self.corpus.documents, chunk, str(spec))
        return self.chunkings[spec_text]

    def embedder(self, name: str) -> Embedder:
        """The embedder, behind the cache, built once."""
        if name not in self.embedders:
            self.embedders[name] = self.project.embedder(name)
        return self.embedders[name]

    def chunk_vectors(self, chunker: str, embedder: str) -> tuple[list[Vector], list[int] | None]:
        """The vectors of a chunking and their token counts (None when the embedder cannot count)."""
        key = (chunker, embedder)
        if key not in self.vectors:
            embedded = self.embedder(embedder).embed([chunk.text for chunk in self.chunked(chunker).chunks])
            self.vectors[key] = (embedded.vectors, embedded.token_counts)
        return self.vectors[key]

    def query_vector(self, embedder: str) -> Callable[[str], Vector]:
        """A function from a question's text to its vector, every question embedded in one go."""
        if embedder not in self.queries:
            texts = sorted({question.question for question in self.questions})
            vectors = self.embedder(embedder).embed(texts, as_query=True).vectors
            self.queries[embedder] = dict(zip(texts, vectors, strict=True))
        known = self.queries[embedder]

        def embed_query(text: str) -> Vector:
            if text not in known:
                known[text] = self.embedder(embedder).embed([text], as_query=True).vectors[0]
            return known[text]

        return embed_query

    def evaluate(self, spec: PipelineSpec) -> Evaluation:
        """Every question through one pipeline, from the run's folder when already measured."""
        saved = run_files.load_evaluation(self.folder, spec)
        if saved is not None:
            return saved
        chunks = self.chunked(spec.chunker).chunks
        needs_vectors = spec.retriever != "bm25" and spec.embedder is not None
        vectors, counts = (
            self.chunk_vectors(spec.chunker, spec.embedder)
            if needs_vectors and spec.embedder
            else (None, None)
        )
        embed_query = self.query_vector(spec.embedder) if spec.embedder and needs_vectors else _no_vectors
        search_of = self._search_of(spec.retriever, embed_query)
        results, timing = run_pipeline(
            chunks,
            search_of,
            vectors,
            self._rerank(spec.reranker),
            self.questions,
            (self.settings, self.tokens),
        )
        evaluation = Evaluation(spec, results, self._costs(spec, (vectors, counts), results, timing))
        run_files.save_evaluation(self.folder, evaluation)
        return evaluation

    def _search_of(
        self, retriever: str, embed_query: Callable[[str], Vector]
    ) -> Callable[[list[str], list[Vector] | None], Search]:
        spec = parse_spec(retriever)
        stage = stages.find("retriever", spec.name)
        check_params(stage.function, spec, injected=RETRIEVER_ARGUMENTS)

        def search_of(texts: list[str], vectors: list[Vector] | None) -> Search:
            built: Search = stage.function(texts, vectors, embed_query, **spec.kwargs())
            return built

        return search_of

    def _rerank(self, reranker: str) -> Rerank | None:
        spec = parse_spec(reranker)
        if spec.name == "none":
            return None
        stage = stages.find("reranker", spec.name)
        check_params(stage.function, spec, injected=RERANKER_INJECTED)
        accepted = inspect.signature(stage.function).parameters
        extra: dict[str, object] = {}
        if "client" in accepted:
            extra["client"] = self.project.client
        if "prompt" in accepted:
            extra["prompt"] = load_prompt("reranker.llm", self.project.config.prompts_dir).text
        if "model" in accepted and "model" not in spec.kwargs():
            extra["model"] = self.project.role("reranker").models[0]
        return functools.partial(stage.function, **spec.kwargs(), **extra)

    def _costs(
        self,
        spec: PipelineSpec,
        embedded: tuple[list[Vector] | None, list[int] | None],
        results: dict[str, QuestionResult],
        timing: Timing,
    ) -> Costs:
        vectors, counts = embedded
        chunks = self.chunked(spec.chunker).chunks
        sizes = counts or [estimate_tokens(chunk.text) for chunk in chunks]
        per_query = [self._top_tokens(chunks, result) for result in results.values()]
        latencies = sorted(timing.query_ms)
        return Costs(
            vectors=len(vectors or []),
            chunk_tokens_median=percentile(sizes, 0.5),
            chunk_tokens_p95=percentile(sizes, 0.95),
            tokens_measured=counts is not None,
            tokens_per_query=statistics.fmean(per_query) if per_query else 0.0,
            latency_ms_p50=round(_at(latencies, 0.5), 2),
            latency_ms_p95=round(_at(latencies, 0.95), 2),
            index_ms=timing.index_ms,
            cost_usd=self._price(spec.embedder, sum(sizes) if vectors else 0),
        )

    def _top_tokens(self, chunks: list[Chunk], result: QuestionResult) -> int:
        """Reference tokens in the top k chunks: what a model would be given to answer."""
        return sum(count_tokens(chunks[index].text) for index in result.final[: self.settings.k])

    def _price(self, embedder: str | None, tokens: int) -> float | None:
        """Dollars for the embedding: local models cost nothing; an endpoint's price must be configured."""
        if embedder is None or not embedder.startswith(ENDPOINT_PREFIX):
            return 0.0
        price = self.project.config.prices.get(embedder)
        return None if price is None else round(price * tokens / 1_000_000, 6)


def _no_vectors(text: str) -> Vector:
    """The query embedder of a pipeline that has none (a lexical retriever never calls it)."""
    del text
    return []


def _at(ordered: list[float], share: float) -> float:
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else 0.0
