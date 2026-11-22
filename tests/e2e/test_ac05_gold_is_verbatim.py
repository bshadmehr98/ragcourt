"""Guarantee 5: gold is verbatim (design §6.2, §16).

A generated quote not found in its document drops the question, and the drop is counted by reason in the
question file and the output.
"""

import json
from pathlib import Path

from ragcourt.testing import ScriptedReplies
from tests.conftest import Run


def test_an_invented_quote_drops_the_question(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    scripted.unverbatim = True
    code, out, _ = run("questions", corpus)
    assert code == 0
    assert "quote not found verbatim" in out
    header = json.loads((project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[0])
    assert header["dropped"]["paraphrase"]["quote not found verbatim"] >= 1
    assert len((project / ".ragcourt" / "questions.jsonl").read_text().splitlines()) == 1  # the header only


def test_kept_quotes_are_spans_of_their_documents(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    assert run("questions", corpus)[0] == 0
    lines = (project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    texts = {path.name: path.read_text() for path in corpus.iterdir()}
    for line in lines:
        question = json.loads(line)
        if not question["document"].endswith(".html"):
            assert texts[question["document"]][question["start"] : question["end"]] == question["quote"]
    assert lines
