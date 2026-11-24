"""Placing the chunk texts of a pipeline ragcourt did not build (change 0006)."""

import json
from pathlib import Path

import pytest

from ragcourt import stages
from ragcourt.core.external import UNPLACED, place_texts, places
from ragcourt.core.fixes import external_fix
from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import token_map
from ragcourt.io import run_files
from ragcourt.types import Document
from ragcourt.types.questions import Question
from ragcourt.types.results import Evaluation, PipelineSpec, QuestionResult

DOCUMENTS = [
    Document("a.md", "Jobs are retried three times.\nThen they are dead.\n\nFooter line."),
    Document("b.md", "Workers send a heartbeat.\n\nFooter line."),
]


def test_a_text_found_once_is_placed_even_with_other_whitespace() -> None:
    placed = place_texts(["Workers send a heartbeat.", "retried three times. Then they"], DOCUMENTS)
    first, second = placed.chunks
    assert (first.document, first.start, first.end, first.index) == ("b.md", 0, 25, 0)
    assert second.document == "a.md" and DOCUMENTS[0].text[second.start : second.end].startswith("retried")
    assert placed.scorable == 2 and not placed.not_found and not placed.several


def test_a_text_not_found_or_found_twice_has_no_place_and_is_counted() -> None:
    placed = place_texts(["Title: Jobs are retried", "Footer line.", "   ", "Then they are dead."], DOCUMENTS)
    assert [chunk.document.startswith(UNPLACED) for chunk in placed.chunks] == [True, True, True, False]
    assert set(placed.own_texts().values()) == {"Title: Jobs are retried", "Footer line.", "   "}
    assert placed.not_found == {0, 2} and placed.several == {1} and placed.scorable == 1
    assert [chunk.index for chunk in placed.chunks] == [0, 1, 2, 3]  # every text keeps its rank


def test_the_pipeline_kind_is_registered_with_its_chunks(registry: None) -> None:
    @stages.pipeline("unit-mine")
    def mine(query: str, depth: int) -> list[str]:
        return [query][:depth]

    @stages.pipeline_chunks("unit-mine")
    def mine_chunks() -> list[str]:
        return ["a"]

    assert "pipeline" in stages.KINDS and "unit-mine" in stages.names("pipeline")
    assert stages.find("pipeline_chunks", "unit-mine").function() == ["a"]
    assert PipelineSpec.external("unit-mine").label == "your pipeline unit-mine"


def test_a_fix_is_confirmed_only_by_a_measured_pipeline_that_hits() -> None:
    def measured(spec: PipelineSpec, hit: float) -> Evaluation:
        return Evaluation(spec, {"q": QuestionResult("q", (), (), {"hit_at_k": hit})})

    own = PipelineSpec("recursive", "fake", "dense")
    mine = measured(PipelineSpec.external("mine"), 1.0)  # your own pipeline never confirms itself
    level, fix = external_fix("retrieval.not_found", "q", [mine, measured(own, 1.0)], own)
    assert level == "confirmed" and "recursive | fake | dense | none reaches the top k" in fix
    level, fix = external_fix("retrieval.not_found", "q", [mine, measured(own, 0.0)], own)
    assert level == "indicated" and "none of the 1 pipelines measured here finds it" in fix
    level, fix = external_fix("retrieval.not_found", "q", [mine], None)
    assert level == "indicated" and "--no-search" in fix


def test_an_exact_place_counts_before_a_whitespace_variant() -> None:
    once = [Document("a.md", "foo  bar baz. later foo bar baz.")]
    assert [place[1] for place in places("foo bar", once)] == [20]  # exactly once: no variant is looked for
    twice = [Document("a.md", "foo  bar baz. later foo\nbar baz.")]
    assert len(places("foo bar", twice)) == 2  # nowhere exactly, twice with other whitespace: several


def test_an_unplaced_text_holds_no_quote_but_its_words_are_counted() -> None:
    text = "Alpha beta gamma delta. The answer is forty two. Omega."
    start = text.index("The answer")
    question = Question(
        "q", "What?", "keyword", "d.md", start, start + 24, text[start : start + 24], "held-out"
    )
    placed = place_texts(
        ["A title my system added to every chunk it returns.", text], [Document("d.md", text)]
    )
    tokens = token_map({"d.md": text, **placed.own_texts()})
    ranking = Ranking(question, placed.chunks, placed.chunks, 2, 10)
    measured = all_metrics(ranking, tokens)
    assert measured["hit_at_k"] == 1.0 and measured["mrr"] == 0.5
    # 11 tokens of the added title and 13 of the document; 6 of them are the quote
    assert measured["token_precision_at_k"] == pytest.approx(6 / 24)
    assert measured["recall_at_budget"] == 0.0  # the title used the whole budget of 10 tokens


def test_a_run_folder_written_before_pipelines_still_loads(tmp_path: Path) -> None:
    spec = PipelineSpec("recursive", "fake", "dense")
    (tmp_path / "configs").mkdir()
    old = {"spec": {"chunker": "recursive", "embedder": "fake", "retriever": "dense", "reranker": "none"}}
    old.update(costs={}, results={})
    run_files.config_path(tmp_path, spec).write_text(json.dumps(old))
    loaded = run_files.load_evaluation(tmp_path, spec)
    assert loaded is not None and loaded.spec == spec and loaded.spec.pipeline is None
