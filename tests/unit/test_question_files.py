"""The question file, user questions, revalidation and the TOML role editor (design §6.3, §6.5, D-031)."""

import json
from pathlib import Path

import pytest

from ragcourt import FormatVersionError
from ragcourt.core.recommend import recommend
from ragcourt.core.user_questions import read_user_questions
from ragcourt.flows.questions import revalidate
from ragcourt.io import question_file
from ragcourt.io.config_template import config_text
from ragcourt.io.toml_edit import set_role, toml_value
from ragcourt.types.questions import Dropped, Question, Span, Verdict


def test_questions_round_trip(tmp_path: Path) -> None:
    question = Question(
        "id1",
        "Q?",
        "distractor",
        "a.md",
        0,
        5,
        "hello",
        "dev",
        None,
        Span("b.md", 1, 2),
        (Verdict("v", passed=True, reason="r"),),
        3,
    )
    dropped = Dropped(
        "keyword", "duplicate", "Q", "quote", (Verdict("x", passed=False, reason="y", by="judge"),), 1
    )
    question_file.start_files(tmp_path, {"corpus_hash": "h"})
    question_file.append(tmp_path, question)
    question_file.append(tmp_path, dropped)
    header, questions, drops = question_file.read_questions(tmp_path)  # type: ignore[misc]
    assert header["format_version"] == "1" and questions == [question] and drops == [dropped]
    question_file.finish(tmp_path, {"complete": True}, [question])
    assert question_file.read_questions(tmp_path)[0]["complete"] is True  # type: ignore[index]
    assert question_file.read_questions(tmp_path / "none") is None


def test_a_newer_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "questions.jsonl").write_text(json.dumps({"format_version": "2"}) + "\n")
    with pytest.raises(FormatVersionError, match="Upgrade ragcourt"):
        question_file.read_questions(tmp_path)


def test_user_questions_directly() -> None:
    texts = {"a.md": "The quote is here. Again.", "b.md": "Again."}
    outcomes = read_user_questions(
        [{"question": "Q", "quote": "quote is here"}, {"quote": "x"}, {"question": "Q2", "quote": "Again."}],
        texts,
    )
    assert isinstance(outcomes[0], Question) and outcomes[0].document == "a.md"
    assert isinstance(outcomes[1], Dropped) and outcomes[1].reason == "no question"
    assert isinstance(outcomes[2], Dropped) and outcomes[2].reason.startswith("ambiguous")


def test_revalidation_moves_or_drops_quotes() -> None:
    moved = Question("1", "Q", "keyword", "a.md", 0, 4, "four")
    gone = Question("2", "Q", "keyword", "a.md", 5, 9, "five")
    other = Question("3", "Q", "keyword", "z.md", 0, 1, "x")
    kept = revalidate([moved, gone, other], {"a.md": "new text: four"})
    assert [(q.id, q.start) for q in kept] == [("1", 10)]


def test_set_role_keeps_everything_else(tmp_path: Path) -> None:
    path = tmp_path / "ragcourt.toml"
    path.write_text("# top\nseed = 1\n\n[models]\n# the judge\njudge = 'a'  # old\n\n[search]\nk = 3\n")
    set_role(path, "judge", toml_value(("b",), as_list=False))
    set_role(path, "embedders", toml_value(("x", "y"), as_list=True))
    assert (
        path.read_text()
        == '# top\nseed = 1\n\n[models]\n# the judge\njudge = "b"\nembedders = ["x", "y"]\n\n[search]\nk = 3\n'
    )
    fresh = tmp_path / "new.toml"
    set_role(fresh, "writer", '"w"')
    assert fresh.read_text() == '[models]\nwriter = "w"\n'
    other = tmp_path / "other.toml"
    other.write_text("seed = 2\n")
    set_role(other, "writer", '"w"')
    assert other.read_text() == 'seed = 2\n\n[models]\nwriter = "w"\n'


def test_recommendations_and_the_template() -> None:
    assert recommend(32, 8).roles["judge"] == ("gemma4",)
    assert "CPU" in recommend(32, None).why
    assert recommend(8, None).roles["writer"] == ("qwen3:4b",)
    text = config_text(recommend(32, 8).roles)
    assert 'judge = "gemma4"' in text and "# writer:" in text
