"""Intervals, ties, leaderboards and the choice on dev (design §8.4, §10.1)."""

from ragcourt.core.leaderboard import Scoring, board, ranked_categories
from ragcourt.core.search import Candidates, choose, step_specs
from ragcourt.core.stats import (
    interval,
    overall_interval,
    paired_difference,
    resamples,
    separable,
    smallest_difference,
)
from ragcourt.types.questions import Question
from ragcourt.types.results import Costs, Evaluation, Interval, PipelineSpec, QuestionResult


def questions(category: str, count: int, split: str = "held-out") -> list[Question]:
    return [Question(f"{category}{n:03d}", "Q", category, "d", 0, 1, "q", split) for n in range(count)]


def evaluation(
    name: str, scores: dict[str, float], members: list[Question], cost: float | None = 0.0, size: float = 10.0
) -> Evaluation:
    results = {
        q.id: QuestionResult(
            q.id, (), (), {"m": scores[q.category], "hit_at_k": scores[q.category], "mrr": 0.0}
        )
        for q in members
    }
    return Evaluation(PipelineSpec(name, "e", "dense"), results, Costs(cost_usd=cost, tokens_per_query=size))


def varied(name: str, members: list[Question], step: int) -> Evaluation:
    results = {}
    for number, q in enumerate(members):
        value = (number * step % 5) / 4
        results[q.id] = QuestionResult(q.id, (), (), {"m": value, "hit_at_k": value, "mrr": 0.0})
    return Evaluation(PipelineSpec(name, "e", "dense"), results, Costs(cost_usd=0.0))


def draws_for(members: list[Question]) -> dict[str, list[list[int]]]:
    groups: dict[str, int] = {}
    for q in members:
        groups[q.category] = groups.get(q.category, 0) + 1
    return {name: resamples(count, 300, 1) for name, count in groups.items()}


def test_intervals() -> None:
    draws = resamples(4, 500, 0)
    assert interval([1.0, 1.0, 1.0, 1.0], draws) == Interval(1.0, 1.0, 1.0)
    spread = interval([0.0, 1.0, 0.0, 1.0], draws)
    assert spread.mean == 0.5 and spread.low < 0.5 < spread.high
    assert interval([], draws) == Interval(0.0, 0.0, 0.0)
    both = overall_interval(
        {"a": [1.0, 1.0], "b": [0.0, 0.0, 0.0, 0.0]}, {"a": resamples(2, 50, 0), "b": resamples(4, 50, 0)}
    )
    assert both.mean == 0.5  # categories weigh the same, whatever their size
    assert overall_interval({}, {}) == Interval(0.0, 0.0, 0.0)


def test_paired_differences() -> None:
    draws = {"a": resamples(6, 400, 0)}
    clear = paired_difference({"a": [1.0] * 6}, {"a": [0.0] * 6}, draws)
    assert separable(clear) and smallest_difference(clear) == 0.0
    noisy = paired_difference({"a": [1, 0, 1, 0, 1, 0]}, {"a": [0, 1, 0, 1, 0, 1]}, draws)
    assert not separable(noisy) and smallest_difference(noisy) > 0


def test_a_clear_winner_and_a_tie() -> None:
    members = questions("keyword", 40)
    draws = draws_for(members)
    good, bad = evaluation("good", {"keyword": 1.0}, members), evaluation("bad", {"keyword": 0.0}, members)
    won = board("chunker", [bad, good], Scoring(members, "m", 30, draws))
    assert won.winner is not None and won.winner.chunker == "good" and won.rows[0].spec.chunker == "good"
    first, second = varied("one", members, 1), varied("two", members, 3)
    tied = board("chunker", [first, second], Scoring(members, "m", 30, draws))
    assert tied.winner is None and tied.rows[1].tied_with_top
    assert tied.smallest_difference["keyword"] >= 0


def test_too_few_and_category_leaders() -> None:
    members = questions("keyword", 40) + questions("numeric", 40) + questions("user", 3)
    draws = draws_for(members)
    a = evaluation("a", {"keyword": 1.0, "numeric": 0.0, "user": 1.0}, members)
    b = evaluation("b", {"keyword": 0.0, "numeric": 0.9, "user": 0.0}, members)
    result = board("chunker", [a, b], Scoring(members, "m", 30, draws))
    assert result.too_few == {"user": 3}
    assert "user" not in ranked_categories(members, 30)[0]
    assert result.category_leaders in ({"numeric": b.spec.label}, {"keyword": a.spec.label})
    assert ranked_categories(questions("x", 3), 30) == (["x"], {"x": 3})  # pooled when none is enough


def test_choice_on_dev_breaks_ties_by_cost_then_size_then_order() -> None:
    dev = questions("keyword", 30, "dev")
    draws = draws_for(dev)
    pricey = evaluation("pricey", {"keyword": 0.5}, dev, cost=1.0)
    free_big = evaluation("free_big", {"keyword": 0.5}, dev, cost=0.0, size=100)
    free_small = evaluation("free_small", {"keyword": 0.5}, dev, cost=0.0, size=10)
    unknown = evaluation("unknown", {"keyword": 0.5}, dev, cost=None)
    choice = choose([pricey, free_big, free_small, unknown], dev, "m", draws)
    assert choice.best.chunker == "free_small" and len(choice.tied) == 3
    clear = choose(
        [evaluation("low", {"keyword": 0.0}, dev), evaluation("high", {"keyword": 1.0}, dev)], dev, "m", draws
    )
    assert clear.best.chunker == "high" and clear.tied == []


def test_greedy_steps() -> None:
    candidates = Candidates(("e1", "e2"), ("c1", "c2"), ("dense", "bm25"), ("llm",))
    first = step_specs("embedder", None, candidates)
    assert [(s.chunker, s.embedder, s.retriever, s.reranker) for s in first] == [
        ("c1", "e1", "dense", "none"),
        ("c1", "e2", "dense", "none"),
    ]
    best = PipelineSpec("c2", "e2", "bm25", "none")
    assert [s.chunker for s in step_specs("chunker", best, candidates)] == ["c1", "c2"]
    assert [s.retriever for s in step_specs("retriever", best, candidates)] == ["dense", "bm25"]
    assert [s.reranker for s in step_specs("reranker", best, candidates)] == ["none", "llm"]
    assert best.label == "c2 | - | bm25 | none"
    assert best.differs_only_in(PipelineSpec("c1", "e2", "bm25", "none")) == ["chunker"]


def test_among_ties_a_higher_dev_score_beats_a_few_tokens_less() -> None:
    dev = questions("keyword", 30, "dev")
    draws = draws_for(dev)

    def noisy(name: str, ones: int, size: int) -> Evaluation:
        results = {q.id: QuestionResult(q.id, (), (), {"m": float(n < ones)}) for n, q in enumerate(dev)}
        return Evaluation(
            PipelineSpec(name, "e", "dense"), results, Costs(cost_usd=0.0, tokens_per_query=size)
        )

    lower_small, higher_big = noisy("lower_small", 15, 300), noisy("higher_big", 18, 310)
    choice = choose([lower_small, higher_big], dev, "m", draws)
    assert choice.tied, "the two must be tied on dev for the tie-break to matter"
    assert choice.best.chunker == "higher_big"


def test_a_kind_of_question_the_choice_fails_is_found() -> None:
    from ragcourt.core.leaderboard import weak_spots

    members = questions("keyword", 40) + questions("paraphrase", 40)
    draws = draws_for(members)
    keyword_only = evaluation("bm25", {"keyword": 1.0, "paraphrase": 0.0}, members)
    both = evaluation("hybrid", {"keyword": 0.9, "paraphrase": 0.5}, members)
    spots = weak_spots([keyword_only, both], keyword_only, Scoring(members, "m", 30, draws))
    assert [(spot.category, spot.better) for spot in spots] == [("paraphrase", both.spec.label)]
    assert weak_spots([keyword_only, both], both, Scoring(members, "m", 30, draws))[0].category == "keyword"


def test_no_weak_spot_on_a_kind_too_few_to_rank() -> None:
    from ragcourt.core.leaderboard import weak_spots

    members = questions("paraphrase", 1)
    draws = draws_for(members)
    a = evaluation("a", {"paraphrase": 0.0}, members)
    b = evaluation("b", {"paraphrase": 1.0}, members)
    assert weak_spots([a, b], a, Scoring(members, "m", 30, draws)) == []
