"""Guarantee 30: models are easy to change (design §11.4, D-031, §16)."""

from pathlib import Path

from ragcourt.testing import FakeOllamaState, ScriptedReplies
from tests.conftest import Run


def test_set_keeps_comments_and_self_tests_a_new_judge(
    project: Path, run: Run, scripted: ScriptedReplies, ollama: tuple[str, FakeOllamaState]
) -> None:
    _, state = ollama
    state.models["other-judge"] = 4096
    toml = project / "ragcourt.toml"
    toml.write_text(
        "# my comment\n"
        + toml.read_text().replace('judge = "fake-chat"', 'judge = "fake-chat"  # who judges')
    )
    code, out, _ = run("models", "set", "judge", "other-judge")
    assert code == 0
    text = toml.read_text()
    assert "# my comment" in text and 'judge = "other-judge"' in text and 'writer = "fake-chat"' in text
    assert "Judge self-test: other-judge" in out
    table = run("models")[1]
    assert "other-judge" in table and str(toml) in table


def test_set_embedders_writes_a_list_and_a_flag_overrides_for_one_run(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies, ollama: tuple[str, FakeOllamaState]
) -> None:
    toml = project / "ragcourt.toml"
    before = toml.read_text()
    code, _, err = run("models", "set", "embedders", "fake-embed,other-embed")
    assert code == 1 and "other-embed is not installed; nothing was changed" in err
    assert toml.read_text() == before  # a model that is not there is never written down
    ollama[1].models["other-embed"] = 2048
    assert run("models", "set", "embedders", "fake-embed,other-embed")[0] == 0
    assert 'embedders = ["fake-embed", "other-embed"]' in (project / "ragcourt.toml").read_text()
    code, out, _ = run("questions", corpus, "--judge", "fake-chat")
    assert code == 0 and "command-line flag" in out


def test_mistakes_are_explained(project: Path, run: Run, scripted: ScriptedReplies) -> None:
    code, _, err = run("models", "set", "ranker", "x")
    assert code == 1 and "ROLE one of writer, judge" in err
    assert run("models", "test", "writer")[0] == 1
    assert run("models", "test", "judge")[0] == 0
