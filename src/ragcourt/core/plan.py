"""The estimate of a run, printed with the plan before any model call (design §10.3).

Times come from measurements on the owner's machine (design/history/0002, 0004): embedding speeds per
model, and chat and reranking times measured with gemma4 on an 8 GB GPU (D-057). They are estimates
and are labelled so.
"""

from __future__ import annotations

from dataclasses import dataclass

# Texts per second, one text per call, measured (history 0002 and 0004).
EMBED_RATE = {
    "nomic-embed-text": 95,
    "mxbai-embed-large": 50,
    "embeddinggemma": 50,
    "bge-m3": 40,
    "all-minilm": 120,
    "qwen3-embedding:0.6b": 8,
}
DEFAULT_EMBED_RATE = 40.0
CHAT_SECONDS = 0.5  # a short call (write, judge, closed-book answer) with gemma4 on an 8 GB GPU
# About 4.6 drafts per kept question and 2.6 calls per draft: 6 s per kept question, measured on the FastAPI
# docs (1,985 drafts, 434 kept, 44 minutes; D-057).
CALLS_PER_QUESTION = 12.0
RERANK_SECONDS = 2.7  # one llm-reranker call over 20 chunks, measured on the same run


@dataclass(frozen=True)
class Workload:
    """What a run will ask the models to do, counted before it starts."""

    questions_to_write: int
    question_total: int
    embedders: tuple[str, ...]
    chunk_counts: dict[str, int]  # chunker spec -> number of chunks
    llm_rerankers: int


@dataclass(frozen=True)
class Estimate:
    """Calls, texts and minutes per step, and the whole."""

    question_calls: int
    embed_texts: int
    rerank_calls: int
    step_minutes: dict[str, float]

    @property
    def minutes(self) -> float:
        """The whole run."""
        return sum(self.step_minutes.values())


def estimate(work: Workload) -> Estimate:
    """An estimate of each step's time from the measured rates."""
    counts = list(work.chunk_counts.values())
    first_chunker = counts[0] if counts else 0
    first_rate = (
        EMBED_RATE.get(work.embedders[0], DEFAULT_EMBED_RATE) if work.embedders else DEFAULT_EMBED_RATE
    )
    embed_step_one = sum(
        (first_chunker + work.question_total) / EMBED_RATE.get(name, DEFAULT_EMBED_RATE)
        for name in work.embedders
    )
    embed_step_two = sum(counts[1:]) / first_rate
    question_calls = int(work.questions_to_write * CALLS_PER_QUESTION)
    rerank_calls = work.question_total * work.llm_rerankers
    steps = {
        "questions": question_calls * CHAT_SECONDS / 60,
        "embedder": embed_step_one / 60,
        "chunker": embed_step_two / 60,
        "retriever": 0.1,
        "reranker": rerank_calls * RERANK_SECONDS / 60,
    }
    texts = (
        first_chunker * len(work.embedders)
        + sum(counts[1:])
        + work.question_total * (len(work.embedders) + 2)
    )
    return Estimate(
        question_calls, texts, rerank_calls, {name: round(value, 2) for name, value in steps.items()}
    )
