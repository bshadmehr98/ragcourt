"""Guarantee 38: a quick look never names a winner (design §16, change 0004)."""

import json
from pathlib import Path

import pytest

from ragcourt.testing import FakeOllamaState, ScriptedReplies
from tests.conftest import Run, results_of

# The default minimum of 30 held-out questions per category holds: 20 questions can never reach it.
TOML = """ollama_url = "{url}"
[models]
writer = "fake-chat"
judge = "fake-chat"
embedders = ["fake-embed"]
reranker = "fake-chat"
[search]
chunkers = ["recursive:size=200,overlap=20", "fixed:size=60,overlap=0"]
resamples = 200
"""


@pytest.fixture
def quick_project(project: Path, ollama: tuple[str, FakeOllamaState]) -> tuple[Path, FakeOllamaState]:
    url, state = ollama
    state.reply = ScriptedReplies()
    (project / "ragcourt.toml").write_text(TOML.format(url=url))
    return project, state


def test_the_plan_says_what_a_quick_look_cannot_tell_before_any_model_call(
    quick_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    _, state = quick_project
    code, out, _ = run("rank", corpus, "--quick")  # no --yes and no terminal: not started
    assert code == 0 and "Not started" in out
    assert state.requests == []
    assert "A quick look: 20 questions per category" in out
    assert "It cannot name a winner" in out
    assert "the same command without --quick" in out


def test_ac38_a_quick_look_never_names_a_winner(
    quick_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = quick_project
    code, out, err = run("rank", corpus, "--quick", "--yes", "--html")
    assert code == 0, err
    results = results_of(project)
    assert results["plan"]["quick"]["per_category"] == 20
    assert results["boards"]
    for board in results["boards"]:
        assert board["indicative"] and board["winner"] is None
        assert board["too_few"] and all(count < 30 for count in board["too_few"].values())
    assert "Winner:" not in out
    assert "these numbers are indicative; no winner" in out
    assert "Smallest difference these questions can tell apart" in out
    assert out.rstrip().count("A quick look: 20 questions per category") == 2  # the plan and the summary
    report = next((project / ".ragcourt" / "runs").glob("*/report.html")).read_text()
    assert "quick look: no winner is named" in report


def test_the_full_run_reuses_the_quick_look_s_questions(
    quick_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = quick_project
    assert run("rank", corpus, "--quick", "--yes")[0] == 0
    questions = project / ".ragcourt" / "questions.jsonl"
    before = [json.loads(line)["id"] for line in questions.read_text().splitlines()[1:]]
    code, out, err = run("rank", corpus, "--questions", "22", "--yes")
    assert code == 0, err
    after = [json.loads(line)["id"] for line in questions.read_text().splitlines()[1:]]
    assert before and set(before) <= set(after)
    assert "writing a new question set" not in out
    assert "quick" not in results_of(project)["plan"]


def test_quick_and_questions_together_are_a_usage_error(
    quick_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    with pytest.raises(SystemExit) as stopped:
        run("rank", corpus, "--quick", "--questions", "5")
    assert stopped.value.code == 2
