"""The scripted model behaves like the model client (design §11.1, §15.2)."""

import pytest

from ragcourt.testing import FakeEmbedder, ScriptedModel
from ragcourt.types import ChatRequest, ModelClient


def test_replies_come_in_order_and_requests_are_recorded() -> None:
    model: ModelClient = ScriptedModel(['{"verdict": "yes"}', '{"verdict": "no"}'])
    first = ChatRequest(model="judge", prompt="Is this valid?")
    second = ChatRequest(model="judge", prompt="And this?", json_reply=False)
    assert model.chat(first) == '{"verdict": "yes"}'
    assert model.chat(second) == '{"verdict": "no"}'
    assert isinstance(model, ScriptedModel)
    assert model.requests == [first, second]


def test_a_reply_function_sees_each_request() -> None:
    model = ScriptedModel(lambda request: request.prompt.upper())
    assert model.chat(ChatRequest(model="m", prompt="hello")) == "HELLO"


def test_running_out_of_replies_says_which_request() -> None:
    model = ScriptedModel(["only one"])
    model.chat(ChatRequest(model="m", prompt="first"))
    with pytest.raises(LookupError, match="has 1 replies but got request 2: 'second'"):
        model.chat(ChatRequest(model="m", prompt="second"))


def test_embeddings_come_from_the_fake_embedder_with_token_counts() -> None:
    model = ScriptedModel(embedder=FakeEmbedder(dimensions=8))
    embedded = model.embed("nomic-embed-text", ["one two", "three"])
    assert embedded.vectors == FakeEmbedder(dimensions=8).embed(["one two", "three"])
    assert embedded.token_counts == [2, 1]
    assert model.embedded == [("nomic-embed-text", ["one two", "three"])]
