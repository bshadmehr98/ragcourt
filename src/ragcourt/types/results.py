"""Pipelines, their measurements, leaderboards and blame (design §8, §9, §13.3). Data only."""

from __future__ import annotations

from dataclasses import dataclass, field

METRICS = (
    "hit_at_k",
    "mrr",
    "ndcg_at_k",
    "recall_at_k",
    "token_precision_at_k",
    "token_iou_at_k",
    "recall_at_budget",
)


@dataclass(frozen=True)
class PipelineSpec:
    """One chunker, one embedder (or none, for a lexical retriever), one retriever and one reranker."""

    chunker: str
    embedder: str | None
    retriever: str
    reranker: str = "none"

    @property
    def label(self) -> str:
        """``chunker | embedder | retriever | reranker``."""
        lexical = self.retriever.split(":", maxsplit=1)[0] == "bm25"  # BM25 uses no embedder
        embedder = "-" if lexical or self.embedder is None else self.embedder
        return " | ".join([self.chunker, embedder, self.retriever, self.reranker])

    def differs_only_in(self, other: PipelineSpec) -> list[str]:
        """The stages in which ``other`` differs from this one."""
        names = ("chunker", "embedder", "retriever", "reranker")
        return [name for name in names if getattr(self, name) != getattr(other, name)]


@dataclass(frozen=True)
class QuestionResult:
    """One question through one pipeline: the chunk indices after retrieval and after reranking."""

    question: str
    retrieved: tuple[int, ...]
    final: tuple[int, ...]
    metrics: dict[str, float] = field(default_factory=dict[str, float])


@dataclass(frozen=True)
class Costs:
    """What a pipeline costs: sizes, tokens, time, money (design §8.3); None where unknown."""

    vectors: int = 0
    chunk_tokens_median: int = 0
    chunk_tokens_p95: int = 0
    tokens_measured: bool = False
    tokens_per_query: float = 0.0
    latency_ms_p50: float = 0.0
    latency_ms_p95: float = 0.0
    index_ms: int = 0
    cost_usd: float | None = None


@dataclass(frozen=True)
class Evaluation:
    """Every question's result for one pipeline, and its costs."""

    spec: PipelineSpec
    results: dict[str, QuestionResult]
    costs: Costs = field(default_factory=Costs)


@dataclass(frozen=True)
class Interval:
    """A mean with its 95% interval."""

    mean: float
    low: float
    high: float


@dataclass(frozen=True)
class BoardRow:
    """One pipeline on a leaderboard: overall and per category, on held-out questions."""

    spec: PipelineSpec
    overall: Interval
    categories: dict[str, Interval]
    tied_with_top: bool = False


@dataclass(frozen=True)
class Board:
    """A leaderboard: rows best first, the winner or the tie, and what each category can tell apart."""

    stage: str
    metric: str
    rows: list[BoardRow]
    winner: PipelineSpec | None  # None when the top entries are not separable
    smallest_difference: dict[str, float]
    too_few: dict[str, int]  # categories with too few held-out questions, and how many they have
    category_leaders: dict[str, str] = field(default_factory=dict[str, str])
    indicative: bool = False  # every category is too few: numbers shown, no winner named


@dataclass(frozen=True)
class Blame:
    """Why one held-out question was missed: a stage, a mechanism, evidence, a level and a fix (§9)."""

    question: str
    text: str
    category: str
    document: str
    quote: str
    context: str  # the quote's surroundings with the chunk boundaries marked
    stage: str
    mechanism: str
    evidence: str
    also_seen: tuple[str, ...]
    level: str  # "confirmed" or "indicated"
    fix: str
