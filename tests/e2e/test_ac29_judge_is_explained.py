"""Guarantee 29: the judge is explained (design §6.6, D-030, §16)."""

from pathlib import Path

from ragcourt.io.prompts import BUNDLED
from ragcourt.testing import ScriptedReplies
from tests.conftest import Run


def test_explained_before_the_first_judge_call(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    code, out, _ = run("questions", corpus)
    assert code == 0
    explanation = out.index("The judge\n=========")
    assert explanation < out.index("Judge self-test")
    paragraph = " ".join(out[explanation : out.index("Judge self-test")].split())
    for words in (
        "fake-chat",
        "never sees chunks or scores",
        "never decides blame",
        "judge.validity",
        "judge.closed_book",
    ):
        assert words in paragraph
    assert out.index("Models\n======") < explanation


def test_prompts_are_shown_exactly(project: Path, run: Run) -> None:
    code, out, _ = run("prompts", "show", "judge.closed_book")
    assert code == 0 and (BUNDLED / "judge.closed_book.txt").read_text() in out
    listing = run("prompts")[1]
    assert "judge.validity" in listing and "bundled" in listing


def test_dropped_questions_show_the_judges_reason(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    scripted.invalid = {"Which statement covers"}
    run("questions", corpus)
    code, out, _ = run("questions", "show", "--dropped", "--reason", "not valid")
    assert code == 0 and "DROPPED: not valid (judge)" in out and "scripted: no" in out
    assert "Q: " in run("questions", "show")[1]


def test_a_replaced_prompt_is_named_with_its_hash_and_retested(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    run("questions", corpus)
    folder = project / "my_prompts"
    folder.mkdir()
    (folder / "judge.validity.txt").write_text(
        (BUNDLED / "judge.validity.txt").read_text() + "\nBe strict.\n"
    )
    text = (project / "ragcourt.toml").read_text()
    (project / "ragcourt.toml").write_text('prompts_dir = "my_prompts"\n' + text)
    code, out, _ = run("questions", corpus)
    assert code == 0
    assert "Replaced by you: judge.validity" in " ".join(out.split())
    assert "writing a new question set" in out
    assert "Judge self-test: fake-chat" in out and "expected" in out  # tested again, case by case
    assert "yours" in run("prompts")[1]
