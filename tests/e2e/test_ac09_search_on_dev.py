"""Guarantee 9: search on dev, report on held-out (design §6.4, §10.1, §16).

Changing only held-out results never changes the chosen pipeline; changing only dev results never changes
a leaderboard number.
"""

from dataclasses import replace

from ragcourt.core.leaderboard import Scoring, board
from ragcourt.core.search import choose
from ragcourt.core.stats import resamples
from ragcourt.types.questions import Question
from ragcourt.types.results import Costs, Evaluation, PipelineSpec, QuestionResult

DEV = [Question(f"d{n}", "Q", "keyword", "x", 0, 1, "q", "dev") for n in range(30)]
HELD = [Question(f"h{n}", "Q", "keyword", "x", 0, 1, "q", "held-out") for n in range(60)]
DRAWS = {"keyword": resamples(60, 300, 0)}
DEV_DRAWS = {"keyword": resamples(30, 300, 0)}


def pipeline(name: str, dev: float, held: float) -> Evaluation:
    results = {}
    for question in DEV + HELD:
        value = dev if question.split == "dev" else held
        results[question.id] = QuestionResult(question.id, (), (), {"m": value})
    return Evaluation(PipelineSpec(name, "e", "dense"), results, Costs())


def test_held_out_results_never_change_the_choice() -> None:
    a, b = pipeline("a", dev=0.9, held=0.1), pipeline("b", dev=0.2, held=0.8)
    assert choose([a, b], DEV, "m", DEV_DRAWS).best.chunker == "a"
    flipped = [pipeline("a", dev=0.9, held=1.0), pipeline("b", dev=0.2, held=0.0)]
    assert choose(flipped, DEV, "m", DEV_DRAWS).best.chunker == "a"


def test_dev_results_never_change_a_leaderboard_number() -> None:
    first = board("x", [pipeline("a", 0.9, 0.3), pipeline("b", 0.1, 0.7)], Scoring(HELD, "m", 30, DRAWS))
    second = board("x", [pipeline("a", 0.0, 0.3), pipeline("b", 1.0, 0.7)], Scoring(HELD, "m", 30, DRAWS))
    assert [(r.spec, r.overall) for r in first.rows] == [(r.spec, r.overall) for r in second.rows]
    assert first.rows[0].spec == replace(first.rows[0].spec)
