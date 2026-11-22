"""Building embedders from names: Ollama models, endpoint models, registered stages (design §7.3)."""

from pathlib import Path

import pytest

from ragcourt import ConfigError
from ragcourt.io.client import Client
from ragcourt.io.embedders import make_embedder
from ragcourt.stages.embedders.ollama import known_prefixes
from ragcourt.testing import FakeEmbedder, FakeOllamaState, fake_endpoint
from ragcourt.types.config import Config, Endpoint


def test_an_ollama_model_measures_its_limit_in_force(ollama: tuple[str, FakeOllamaState]) -> None:
    url, state = ollama
    embedder = make_embedder("fake-embed", Client(Config(project=Path(), ollama_url=url)))
    assert embedder.max_tokens == 64
    assert embedder.embed(["one two"]).token_counts == [2]
    probe = next(body for path, body in state.requests if path == "/api/embed")
    assert len(probe["input"][0].split()) > 64


def test_documented_prefixes_are_used_and_can_be_changed(ollama: tuple[str, FakeOllamaState]) -> None:
    url, state = ollama
    state.models["nomic-embed-text"] = 2048
    client = Client(Config(project=Path(), ollama_url=url))
    embedder = make_embedder("nomic-embed-text", client)
    embedder.embed(["the chunk"])
    embedder.embed(["the question"], as_query=True)
    sent = [body["input"][0] for path, body in state.requests if path == "/api/embed"][-2:]
    assert sent == ["search_document: the chunk", "search_query: the question"]
    plain = make_embedder("ollama:model=nomic-embed-text,query_prefix=,document_prefix=", client)
    assert (plain.query_prefix, plain.document_prefix) == ("", "")  # type: ignore[attr-defined]
    assert known_prefixes("mxbai-embed-large:latest")[1] == ""
    assert known_prefixes("unknown") == ("", "")


def test_endpoint_and_registered_embedders() -> None:
    with fake_endpoint() as (url, _):
        client = Client(Config(project=Path(), endpoints={"e": Endpoint("e", url)}))
        remote = make_embedder("endpoint:e/text-embed", client)
        assert remote.max_tokens is None and remote.embed(["a"]).token_counts is None
        fake = make_embedder("fake:max_tokens=7", client)
        assert isinstance(fake, FakeEmbedder) and fake.max_tokens == 7
        with pytest.raises(ConfigError, match="has no parameter 'nope'"):
            make_embedder("fake:nope=1", client)
