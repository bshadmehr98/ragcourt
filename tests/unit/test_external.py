"""Placing the chunk texts of a pipeline ragcourt did not build (change 0006)."""

from ragcourt import stages
from ragcourt.core.external import NOWHERE, place_texts
from ragcourt.core.fixes import external_fix
from ragcourt.types import Document
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
    assert [chunk.document for chunk in placed.chunks] == [NOWHERE, NOWHERE, NOWHERE, "a.md"]
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
    level, fix = external_fix("retrieval.not_found", "q", [mine, measured(own, 1.0)])
    assert level == "confirmed" and "recursive | fake | dense | none reaches the top k" in fix
    level, fix = external_fix("retrieval.not_found", "q", [mine, measured(own, 0.0)])
    assert level == "indicated" and "none of the 1 pipelines measured here finds it" in fix
    level, fix = external_fix("retrieval.not_found", "q", [mine])
    assert level == "indicated" and "--no-search" in fix
