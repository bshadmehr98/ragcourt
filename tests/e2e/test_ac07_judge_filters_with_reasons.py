"""Guarantee 7: the judge filters, with its reasons (design §6.2, §6.6, §16)."""

import json
from pathlib import Path

from ragcourt.testing import ScriptedReplies
from tests.conftest import Run


def records(project: Path, name: str) -> list[dict]:  # type: ignore[type-arg]
    lines = (project / ".ragcourt" / name).read_text().splitlines()
    rows = [json.loads(line) for line in lines]
    return rows[1:] if name == "questions.jsonl" else rows


def test_known_unknown_and_invalid(project: Path, corpus: Path, run: Run, scripted: ScriptedReplies) -> None:
    scripted.known = {"Which number is given"}
    scripted.invalid = {"What does the documentation say about"}
    code, _, _ = run("questions", corpus)
    assert code == 0
    dropped = records(project, "questions.dropped.jsonl")
    kept = records(project, "questions.jsonl")
    by_reason = {item["reason"] for item in dropped}
    assert "answerable without the documents (judge)" in by_reason
    assert "not valid (judge)" in by_reason
    closed = next(item for item in dropped if item["reason"].startswith("answerable"))
    assert "scripted: correct" in closed["verdicts"][-1]["reason"]
    for question in kept:
        last = question["verdicts"][-1]
        assert last["check"] == "answerable without documents"
        assert last["reason"] == "the writer answered UNKNOWN; no judge call"
        assert all(verdict["reason"] for verdict in question["verdicts"])


def test_a_users_question_is_never_dropped_by_the_judge(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies, tmp_path: Path
) -> None:
    scripted.invalid = {"Is the dashboard"}
    scripted.known = {"Is the dashboard"}
    mine = tmp_path / "mine.jsonl"
    mine.write_text(
        json.dumps(
            {
                "question": "Is the dashboard exposed to the internet?",
                "quote": "The dashboard has no login of its own.",
            }
        )
        + "\n"
    )
    assert run("questions", corpus, "--questions-file", mine)[0] == 0
    users = [question for question in records(project, "questions.jsonl") if question["category"] == "user"]
    assert len(users) == 1 and users[0]["document"] == "security.md"
    assert [verdict["check"] for verdict in users[0]["verdicts"]] == ["quote found verbatim"]
