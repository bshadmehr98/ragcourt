"""Guarantees 12, 14, 16, 23, 26, 28, 32 and 33, closing the gaps the test audit found (design §16)."""

import json
import re
import shutil
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from ragcourt.core.leaderboard import Scoring, board
from ragcourt.core.stats import resamples
from ragcourt.flows import rank as rank_flow
from ragcourt.flows.probes import Prober
from ragcourt.io.rank_output import board_text
from ragcourt.io.result_data import board_data
from ragcourt.testing import FakeOllamaState
from ragcourt.types.questions import Question
from ragcourt.types.results import Costs, Evaluation, PipelineSpec, QuestionResult
from tests.conftest import Run, results_of

HELD = [Question(f"h{n:02d}", "Q", "keyword", "x", 0, 1, "q", "held-out") for n in range(40)]


def pipeline(name: str, values: list[float]) -> Evaluation:
    results = {q.id: QuestionResult(q.id, (), (), {"m": v}) for q, v in zip(HELD, values, strict=True)}
    return Evaluation(PipelineSpec(name, "e", "dense"), results, Costs())


def test_ac12_a_clear_difference_names_a_winner_and_a_noisy_one_does_not() -> None:
    scoring = Scoring(HELD, "m", 30, {"keyword": resamples(40, 500, "0:keyword")})
    clear = board("chunker", [pipeline("good", [1.0] * 40), pipeline("bad", [0.0] * 40)], scoring)
    assert "Winner: good | e | dense | none." in board_text(board_data(clear), None)
    noisy_a = pipeline("a", [float(n % 2) for n in range(40)])
    noisy_b = pipeline("b", [float((n + 1) % 2) for n in range(40)])
    tied = board("chunker", [noisy_a, noisy_b], scoring)
    text = board_text(board_data(tied), None)
    assert "No significant difference between" in text and "Winner" not in text
    few = board("chunker", [noisy_a, noisy_b], Scoring(HELD, "m", 50, scoring.draws))
    assert "too few held-out questions to rank" in board_text(board_data(few), None) and few.winner is None


def test_ac28_the_plan_is_printed_before_the_first_request(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, state = rank_project
    seen: list[int] = []
    real = rank_flow.plan_text

    def watched(plan, guess):  # type: ignore[no-untyped-def]
        seen.append(len(state.requests))
        return real(plan, guess)

    monkeypatch.setattr(rank_flow, "plan_text", watched)
    assert run("rank", corpus, "--yes")[0] == 0
    assert seen == [0] and state.requests


def test_ac16_a_step_over_the_budget_stops_with_finished_steps_kept(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = rank_project
    ticks = iter(range(0, 10_000, 600))  # every look at the rank flow's clock is ten minutes later
    monkeypatch.setattr(rank_flow, "time", SimpleNamespace(monotonic=lambda: float(next(ticks))))
    code, out, err = run("rank", corpus, "--yes", "--budget-minutes", "25")
    assert code == 4 and "over the budget" in err and "Finished steps:" in err
    assert "Leaderboard" in out
    folder = next((project / ".ragcourt" / "runs").glob("*"))
    assert (folder / "partial.json").is_file() and not (folder / "results.json").exists()
    monkeypatch.setattr(rank_flow, "time", time)
    assert run("rank", corpus, "--yes", "--resume")[0] == 0
    assert (folder / "results.json").is_file()


def test_ac26_a_resumed_run_measures_only_what_was_left(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = rank_project
    assert run("rank", corpus, "--yes")[0] == 0
    total = len(results_of(project)["configurations"])
    shutil.rmtree(project / ".ragcourt" / "runs")
    real = rank_flow.Evaluator.evaluate
    calls = {"count": 0, "measured": 0}

    def stop_after_three(self, spec):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] > 3:
            raise KeyboardInterrupt
        return real(self, spec)

    real_costs = rank_flow.Evaluator._costs  # called once per pipeline actually measured

    def counted(self, *args):  # type: ignore[no-untyped-def]
        calls["measured"] += 1
        return real_costs(self, *args)

    monkeypatch.setattr(rank_flow.Evaluator, "_costs", counted)
    monkeypatch.setattr(rank_flow.Evaluator, "evaluate", stop_after_three)
    assert run("rank", corpus, "--yes")[0] == 130
    before = calls["measured"]
    monkeypatch.setattr(rank_flow.Evaluator, "evaluate", real)
    code, out, _ = run("rank", corpus, "--yes", "--resume")
    assert code == 0 and "Resuming" in out
    assert before > 0 and calls["measured"] == total  # nothing measured twice


def test_ac23_no_address_of_any_kind_in_the_report(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    assert run("rank", corpus, "--yes", "--html")[0] == 0
    report = next((project / ".ragcourt" / "runs").glob("*/report.html")).read_text()
    assert not re.search(r"(src|href|url)\s*[=(]\s*['\"]?(https?:)?//", report, re.I)
    tied_boards = [b for b in results_of(project)["boards"] if not b["winner"]]
    if tied_boards:
        assert "No significant difference at the top" in report or "indicative" in report


def test_ac14_a_confirmed_fix_names_a_measured_configuration(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    assert run("rank", corpus, "--yes")[0] == 0
    results = results_of(project)
    measured = {config["label"] for config in results["configurations"]}
    for blame in results["blames"]:
        if blame["level"] == "confirmed":
            value = blame["fix"].split(": ")[1].split(" finds it")[0].split(" ", 1)[1]
            assert any(value in label for label in measured)


def test_ac32_too_few_to_rank_is_said_and_kept_out(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    toml = project / "ragcourt.toml"
    toml.write_text(toml.read_text().replace("min_held_out = 2", "min_held_out = 4"))
    code, out, _ = run("rank", corpus, "--yes")
    assert code == 0
    for board_ in results_of(project)["boards"]:
        for name, count in board_["too_few"].items():
            assert count < 4 and f"{name}: too few to rank ({count} held-out questions)." in out


def test_ac33_the_probes_change_the_blame(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _ = rank_project
    args = ("rank", corpus, "--yes", "--retrievers", "dense", "--rerankers", "none", "--embedders", "fake")
    assert run(*args)[0] == 0
    before = [blame["mechanism"] for blame in results_of(project)["blames"]]
    shutil.rmtree(project / ".ragcourt" / "runs")
    monkeypatch.setattr(Prober, "_quote_alone", lambda self, question: True)
    assert run(*args)[0] == 0
    after = [blame["mechanism"] for blame in results_of(project)["blames"]]
    lost = before.count("embedder.meaning") + before.count("chunker.diluted")
    assert after.count("chunker.diluted") >= lost > 0  # every clean chunk not retrieved is now "diluted"
    assert "embedder.meaning" not in after or lost == 0


def test_a_held_out_winner_other_than_the_dev_choice_is_pointed_out() -> None:
    scoring = Scoring(HELD, "m", 30, {"keyword": resamples(40, 500, "0:keyword")})
    clear = board_data(
        board("reranker", [pipeline("good", [1.0] * 40), pipeline("bad", [0.0] * 40)], scoring)
    )
    assert "Note: on held-out questions good | e | dense | none is separably better" in board_text(
        clear, "bad | e | dense | none"
    )
    assert "Note:" not in board_text(clear, "good | e | dense | none (tied on dev with 1 more)")


def test_a_run_on_your_own_questions_only_calls_no_writer_or_judge(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, tmp_path: Path
) -> None:
    project, _ = rank_project
    toml = project / "ragcourt.toml"
    toml.write_text(toml.read_text().replace("[questions]", "[questions]\ncategories = []"))
    texts = {path.name: path.read_text() for path in corpus.iterdir() if path.suffix == ".md"}
    rows = []
    for name, text in sorted(texts.items()):
        for sentence in [line for line in text.splitlines() if len(line.split()) >= 8][:2]:
            rows.append(
                json.dumps({"question": f"What does {name} say here?", "quote": sentence, "document": name})
            )
    mine = tmp_path / "mine.jsonl"
    mine.write_text("\n".join(rows) + "\n")
    code, out, err = run("rank", corpus, "--yes", "--questions-file", mine)
    assert code == 0, err
    assert f"use your {len(rows)} questions; none to write" in out
    assert "only your own questions are used" in out and "Judge self-test" not in out
    assert set(results_of(project)["questions"]["by_category"]) == {"user"}
