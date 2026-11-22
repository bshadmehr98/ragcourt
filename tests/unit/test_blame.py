"""Blame: each mechanism's planted case and near miss, the order, fixes, levels and ceilings (§9)."""

from dataclasses import replace

import pytest

from ragcourt.core.blame import MEANINGS, MECHANISM_NAMES, cause, mechanisms_holding
from ragcourt.core.blame.facts import Facts
from ragcourt.core.ceilings import ceilings
from ragcourt.core.fixes import FIXES, fix_for
from ragcourt.types import Chunk
from ragcourt.types.questions import Question, Span
from ragcourt.types.results import Blame, Costs, Evaluation, PipelineSpec, QuestionResult

TEXT = "x" * 100 + " The quote sits here and answers it. " + "y" * 100
START, END = 101, 136
QUESTION = Question("q1", "Where?", "keyword", "d.md", START, END, TEXT[START:END], "held-out")


def chunks(*spans: tuple[int, int]) -> list[Chunk]:
    return [Chunk("d.md", number, start, end, TEXT[start:end]) for number, (start, end) in enumerate(spans)]


HOLDING = chunks((0, 100), (90, 150), (150, 237))  # chunk 1 holds the quote


def facts(**changes: object) -> Facts:
    base = Facts(
        QUESTION,
        HOLDING,
        retrieved=(0, 2),
        final=(0, 2),
        k=1,
        retriever="dense",
        reranker="none",
        chunk_tokens=[25, 15, 22],
        quote_tokens=8,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


PLANTED = {
    "chunker.too_small": {"chunks": chunks((0, 110), (110, 237)), "chunk_tokens": [5, 5]},
    "chunker.split": {"chunks": chunks((0, 120), (120, 237))},
    "chunker.dropped": {"chunks": chunks((0, 105), (130, 237))},
    "chunker.over_limit": {"limit": 10, "quote_end_tokens": 12},
    "chunker.diluted": {"quote_alone_reaches": True},
    "embedder.exact_words": {"bm25_rank": 3},
    "embedder.distracted": {"twin_chunks": frozenset({0})},
    "embedder.meaning": {"other_embedders": {"other": None}},
    "retriever.keyword_only": {"retriever": "bm25", "dense_rank": 2},
    "retriever.fusion": {"retriever": "hybrid", "bm25_rank": 4},
    "retriever.crowded": {"retriever": "bm25", "duplicates": frozenset({0, 2})},
    "ranking.reranker_demoted": {"retrieved": (1, 0), "final": (0, 1), "reranker": "llm"},
    "ranking.distracted": {"retrieved": (0, 1), "final": (0, 1), "twin_chunks": frozenset({0})},
    "ranking.duplicates": {
        "retrieved": (0, 2, 1),
        "final": (0, 2, 1),
        "k": 2,
        "duplicates": frozenset({0, 2}),
    },
    "ranking.not_rescued": {"retrieved": (0, 1), "final": (0, 1)},
}
NEAR_MISSES = {
    "chunker.too_small": {"chunks": chunks((0, 120), (120, 237)), "chunk_tokens": [50, 50]},
    "chunker.split": {},
    "chunker.dropped": {"chunks": chunks((0, 120), (120, 237))},
    "chunker.over_limit": {"limit": 20, "quote_end_tokens": 12},
    "chunker.diluted": {"quote_alone_reaches": False},
    "embedder.exact_words": {"bm25_rank": None},
    "embedder.distracted": {"twin_chunks": frozenset({5})},
    "embedder.meaning": {"quote_alone_reaches": True},
    "retriever.keyword_only": {"retriever": "bm25"},
    "retriever.fusion": {"retriever": "hybrid"},
    "retriever.crowded": {"retriever": "bm25", "duplicates": frozenset({0})},
    "ranking.reranker_demoted": {"retrieved": (0, 1), "final": (0, 1), "reranker": "llm"},
    "ranking.distracted": {"retrieved": (0, 1), "final": (0, 1)},
    "ranking.duplicates": {"retrieved": (0, 1), "final": (0, 1), "k": 1},
    "ranking.not_rescued": {"retrieved": (1, 0), "final": (1, 0)},
}


def test_every_mechanism_has_a_planted_case_and_a_meaning() -> None:
    assert sorted(PLANTED) == sorted(MECHANISM_NAMES) == sorted(MEANINGS) == sorted(FIXES)


@pytest.mark.parametrize("mechanism", MECHANISM_NAMES)
def test_the_planted_case_gives_the_mechanism(mechanism: str) -> None:
    found = [name for name, _ in mechanisms_holding(facts(**PLANTED[mechanism]))]
    assert mechanism in found


@pytest.mark.parametrize("mechanism", MECHANISM_NAMES)
def test_the_near_miss_does_not(mechanism: str) -> None:
    found = [name for name, _ in mechanisms_holding(facts(**NEAR_MISSES[mechanism]))]
    assert mechanism not in found


def test_one_cause_the_first_in_order_and_the_rest_also_seen() -> None:
    mechanism, evidence, also = cause(facts(limit=10, quote_end_tokens=12, quote_alone_reaches=True))
    assert mechanism == "chunker.over_limit" and "token 12" in evidence and "chunker.diluted" in also


def test_a_miss_always_gets_a_cause() -> None:
    assert cause(facts(retrieved=(0, 1), final=(0, 1), k=1))[0] == "ranking.not_rescued"
    assert cause(facts(quote_alone_reaches=True, retriever="bm25"))[0] == "embedder.meaning"


def evaluation(spec: PipelineSpec, hit: float) -> Evaluation:
    return Evaluation(spec, {"q1": QuestionResult("q1", (), (), {"hit_at_k": hit})}, Costs())


def test_confirmed_needs_a_measured_alternative_differing_only_in_that_stage() -> None:
    chosen = PipelineSpec("c1", "e1", "dense", "none")
    other_chunker = evaluation(PipelineSpec("c2", "e1", "dense", "none"), 1.0)
    level, fix = fix_for("chunker.split", "q1", chosen, [other_chunker])
    assert level == "confirmed" and "with chunker c2 it reaches the top k" in fix
    two_changes = evaluation(PipelineSpec("c2", "e2", "dense", "none"), 1.0)
    level, fix = fix_for("chunker.split", "q1", chosen, [two_changes])
    assert level == "indicated" and "--chunkers" in fix and "not measured" in fix
    level, fix = fix_for(
        "chunker.over_limit", "q1", chosen, [evaluation(PipelineSpec("c1", "e2", "dense", "none"), 1.0)]
    )
    assert level == "confirmed" and "embedder e2" in fix
    level, fix = fix_for("embedder.meaning", "q1", chosen, [evaluation(chosen, 0.0)])
    assert fix == "no tested embedder connects this question to its answer"
    level, fix = fix_for(
        "chunker.split", "q1", chosen, [evaluation(PipelineSpec("c2", "e1", "dense", "none"), 0.0)]
    )
    assert level == "indicated" and "it misses the top k there too: chunker c2" in fix


def blame(question: str, stage: str) -> Blame:
    return Blame(question, "t", "keyword", "d", "q", "", stage, f"{stage}.x", "", (), "indicated", "")


def test_ceilings_are_non_increasing_and_gaps_are_the_counts() -> None:
    members = [Question(f"q{n}", "Q", "keyword", "d", 0, 1, "q", "held-out") for n in range(10)]
    found = ceilings(
        members,
        [blame("q0", "chunker"), blame("q1", "embedder"), blame("q2", "retriever"), blame("q3", "ranking")],
    )
    overall = found["overall"]
    assert (overall.chunker, overall.retrieval, overall.hit_at_k) == (0.9, 0.7, 0.6)
    assert found["keyword"].questions == 10 and ceilings([], [])["overall"].questions == 0


def test_twin_spans_are_kept_for_distractors() -> None:
    twin = Question(
        "q2", "Q", "distractor", "d.md", START, END, QUESTION.quote, "held-out", twin=Span("d.md", 0, 50)
    )
    assert twin.twin is not None and twin.twin.end == 50
