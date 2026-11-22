"""Guarantee 31: categories are real (design §6.7, §16).

Every kept question passed its category's code check (and the judge where §6.7 asks); one that fails is
dropped and counted, never kept under that category.
"""

import json
from pathlib import Path

from ragcourt.core.categories import CATEGORIES
from ragcourt.core.windows import index_corpus
from ragcourt.io.documents import load_documents
from ragcourt.testing import ScriptedReplies
from ragcourt.types.questions import Offer, Window
from tests.conftest import Run


def test_every_kept_question_passed_its_category(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    assert run("questions", corpus)[0] == 0
    kept = [
        json.loads(line) for line in (project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    ]
    index = index_corpus(load_documents(corpus).documents, 2000)
    assert {question["category"] for question in kept} >= {"keyword", "exact_term", "negation", "numeric"}
    for question in kept:
        assert question["verdicts"][0]["check"] == "code rules" and question["verdicts"][0]["passed"]
        offer = Offer(Window(question["document"], 0, 1), question["term"], None)
        if question["category"] != "distractor":
            assert (
                CATEGORIES[question["category"]].check(question["question"], question["quote"], offer, index)
                is None
            )
        if CATEGORIES[question["category"]].JUDGE:
            assert question["verdicts"][1]["check"].startswith("of its category")


def test_a_question_of_the_wrong_kind_is_dropped_and_counted(
    project: Path, corpus: Path, run: Run, scripted: ScriptedReplies
) -> None:
    run("questions", corpus)
    header = json.loads((project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[0])
    kept = {
        json.loads(line)["question"]
        for line in (project / ".ragcourt" / "questions.jsonl").read_text().splitlines()[1:]
    }
    dropped = [
        json.loads(line)
        for line in (project / ".ragcourt" / "questions.dropped.jsonl").read_text().splitlines()
    ]
    wrong_kind = [item for item in dropped if item["reason"].startswith("not of its category")]
    assert wrong_kind
    for item in wrong_kind:
        assert header["dropped"][item["category"]][item["reason"]] >= 1
        assert item["question"] not in kept or item["category"] == "exact_term"
