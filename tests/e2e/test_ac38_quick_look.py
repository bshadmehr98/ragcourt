"""Guarantee 38: a quick look never names a winner (design §16, change 0004)."""

import json
from pathlib import Path

import pytest

from ragcourt import ConfigError
from ragcourt.flows.run_plan import check_quick_set
from ragcourt.io.project import ProjectOptions, open_project
from ragcourt.testing import FakeOllamaState, ScriptedReplies
from ragcourt.types.questions import Question
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
    minutes = results["plan"]["quick"]["full_run_minutes"]
    assert minutes > 0 and f"about {minutes:.0f} minutes more (estimated)" in out
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


def test_a_quick_look_is_refused_when_it_could_name_a_winner(
    quick_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, state = quick_project
    toml = project / "ragcourt.toml"
    toml.write_text(toml.read_text() + "[questions]\nmin_held_out = 5\n")
    code, out, err = run("rank", corpus, "--quick", "--yes")
    assert code == 1 and "it would name winners" in err and "min_held_out is 5" in err
    assert "Plan" not in out and state.requests == []


def test_a_quick_look_is_refused_on_a_question_set_large_enough_to_rank(tmp_path: Path) -> None:
    def held(count: int) -> list[Question]:
        return [Question(f"q{n}", "Q", "keyword", "d", 0, 1, "q", "held-out") for n in range(count)]

    project = open_project(ProjectOptions(tmp_path))
    check_quick_set(project, held(29))  # under the minimum of 30: every board stays indicative
    with pytest.raises(ConfigError, match=r"large enough to rank \(30 questions\).*without --quick"):
        check_quick_set(project, held(30))
