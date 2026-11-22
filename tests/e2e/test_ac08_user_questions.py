"""Guarantee 8: user questions are accepted with quote validation (design §6.3, §16)."""

import json
from pathlib import Path

from ragcourt.testing import ScriptedReplies
from tests.conftest import Run

ROWS = [
    {
        "question": "How long is a dead job kept?",
        "quote": "A dead job stays in the table with its last error until someone looks at it.",
    },
    {"question": "Which header line?", "quote": "Larkspur Docs · version 3.2"},
    {"question": "No quote here?"},
    {"question": "Invented?", "quote": "Larkspur runs on the moon."},
    {"question": "With a document", "quote": "Larkspur Docs · version 3.2", "document": "queues.md"},
    {"question": "Wrong document", "quote": "x", "document": "nope.md"},
]


def test_user_questions_are_validated_by_their_quote(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies, tmp_path: Path
) -> None:
    mine = tmp_path / "mine.jsonl"
    mine.write_text("\n".join(json.dumps(row) for row in ROWS) + "\n")
    code, out, _ = run("questions", corpus, "--questions-file", mine)
    assert code == 0
    kept = [
        json.loads(line) for line in (project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    ]
    users = sorted(question["question"] for question in kept if question["category"] == "user")
    assert users == ["How long is a dead job kept?", "With a document"]
    dropped = [
        json.loads(line)
        for line in (project / ".ragcourt" / "questions.dropped.jsonl").read_text().splitlines()
    ]
    reasons = {item["question"]: item["reason"] for item in dropped if item["category"] == "user"}
    assert reasons["Which header line?"].startswith("ambiguous: the quote is in")
    assert reasons["No quote here?"].startswith("no quote")
    assert reasons["Invented?"] == "quote not found verbatim"
    assert reasons["Wrong document"] == "no document 'nope.md'"
    assert "user" in out


def test_a_broken_line_names_the_file_and_line(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies, tmp_path: Path
) -> None:
    mine = tmp_path / "bad.jsonl"
    mine.write_text('{"question": "ok", "quote": "x"}\nnot json\n')
    code, _, err = run("questions", corpus, "--questions-file", mine)
    assert code == 1 and "line 2 is not JSON" in err
