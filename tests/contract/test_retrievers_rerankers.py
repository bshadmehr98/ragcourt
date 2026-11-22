"""Retrievers and rerankers keep their contracts; adapters translate and say which extra they need (§7)."""

from importlib.util import find_spec

import pytest

from ragcourt import ExtraMissing, stages
from ragcourt.core.pipeline import reorder
from ragcourt.stages.rerankers.llm import read_order
from ragcourt.testing import FakeEmbedder, ScriptedModel

CHUNKS = [
    "the worker retries failed jobs",
    "cron schedules the sweeper",
    "dashboards show queue age",
    "retries wait ten seconds",
]
EMBEDDER = FakeEmbedder()
VECTORS = EMBEDDER.embed(CHUNKS).vectors


def embed_query(text: str) -> list[float]:
    return EMBEDDER.embed([text], as_query=True).vectors[0]


@pytest.mark.parametrize("name", ["dense", "bm25", "hybrid"])
def test_retrievers_rank_by_relevance_with_deterministic_ties(name: str) -> None:
    search = stages.find("retriever", name).function(CHUNKS, VECTORS, embed_query)
    ranked = search("how long do retries wait", 3)
    assert 1 <= len(ranked) <= 3 and ranked[0][0] == 3
    assert ranked == search("how long do retries wait", 3)
    scores = [score for _, score in ranked]
    assert scores == sorted(scores, reverse=True)


def test_bm25_ties_go_by_index_and_dense_needs_vectors() -> None:
    search = stages.find("retriever", "bm25").function(["a", "a", "b"], None, embed_query)
    assert [index for index, _ in search("a", 3)] == [0, 1]  # ties by index; no shared word, not retrieved
    assert search("zzz", 3) == []
    with pytest.raises(Exception, match="needs an embedder"):
        stages.find("retriever", "dense").function(CHUNKS, None, embed_query)


def test_none_keeps_the_order_and_reorder_breaks_ties_by_position() -> None:
    scores = stages.find("reranker", "none").function("q", ["a", "b", "c"])
    assert reorder([7, 8, 9], scores) == [7, 8, 9]
    assert reorder([7, 8, 9], [1.0, 3.0, 1.0]) == [8, 7, 9]


def test_the_llm_reranker_orders_the_top_and_keeps_the_rest() -> None:
    model = ScriptedModel(['{"order": [3, 1]}'])
    scores = stages.find("reranker", "llm").function(
        "q", ["a", "b", "c", "d"], client=model, prompt="{{question}} {{passages}}", top=3
    )
    assert reorder([0, 1, 2, 3], scores) == [2, 0, 1, 3]
    assert "[3] c" in model.requests[0].prompt
    assert read_order("no json", 2) == [0, 1] and read_order('{"order": [9, 2, 2]}', 2) == [1, 0]
    assert read_order('{"order": "x"}', 2) == [0, 1] and read_order("{bad json}", 2) == [0, 1]


def test_the_endpoint_reranker_asks_the_client() -> None:
    scores = stages.find("reranker", "endpoint").function(
        "cat food", ["dog", "cat food"], client=ScriptedModel(), model="endpoint:x/y"
    )
    assert scores == [0.0, 2.0]


@pytest.mark.skipif(find_spec("sentence_transformers") is not None, reason="the local extra is installed")
@pytest.mark.parametrize(("kind", "name"), [("embedder", "st"), ("reranker", "cross-encoder")])
def test_the_local_extra_is_named_when_missing(kind: str, name: str) -> None:
    function = stages.find(kind, name).function
    with pytest.raises(ExtraMissing, match=r"ragcourt\[local\]"):
        function() if kind == "embedder" else function("q", ["a"])


@pytest.mark.parametrize(
    "name",
    ["chonkie.token", "chonkie.sentence", "chonkie.recursive", "langchain.recursive", "langchain.markdown"],
)
def test_library_adapters_return_text_of_the_document(name: str) -> None:
    if find_spec(name.split(".", maxsplit=1)[0].replace("langchain", "langchain_text_splitters")) is None:
        pytest.skip("extra not installed")
    text = "# Title\n\n" + "A sentence about retries. " * 80 + "\n\n## Two\n\n" + "Another one here. " * 40
    pieces = (
        stages.find("chunker", name).function(text, size=200)
        if "chonkie" in name
        else stages.find("chunker", name).function(text, size=300, overlap=0)
    )
    assert pieces and all(piece.strip() in text for piece in pieces)
