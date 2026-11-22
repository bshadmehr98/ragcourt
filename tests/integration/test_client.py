"""The one client against a fake Ollama and a fake endpoint (design §11.1, D-041)."""

from pathlib import Path

import pytest

from ragcourt import ConfigError, EndpointError
from ragcourt.io.client import Client
from ragcourt.io.http import request_json
from ragcourt.testing import FakeEndpointState, FakeOllamaState, fake_endpoint
from ragcourt.types import ChatRequest
from ragcourt.types.config import Config, Endpoint


def client_for(url: str, endpoints: dict[str, Endpoint] | None = None) -> Client:
    return Client(Config(project=Path(), ollama_url=url, endpoints=endpoints or {}), sleep=lambda _: None)


def test_ollama_embeds_one_text_per_call_with_its_count(ollama: tuple[str, FakeOllamaState]) -> None:
    url, state = ollama
    embedded = client_for(url).embed("fake-embed", ["one two", "three four five"])
    assert embedded.token_counts == [2, 3]
    embeds = [body for path, body in state.requests if path == "/api/embed"]
    assert [len(body["input"]) for body in embeds] == [1, 1]
    assert embeds[0]["options"] == {"num_ctx": 64, "num_batch": 64}


def test_ollama_show_chat_and_installed(ollama: tuple[str, FakeOllamaState]) -> None:
    url, state = ollama
    state.reply = '<think>hmm</think> {{"echo": "{}"}}'.format
    client = client_for(url)
    info = client.show("fake-embed")
    assert (info.context_length, info.size_bytes, info.digest) == (64, 1000, "sha-fake-embed")
    assert client.chat(ChatRequest("fake-chat", "hi")) == '{"echo": "hi"}'
    chat = next(body for path, body in state.requests if path == "/api/chat")
    assert (
        chat["format"] == "json"
        and chat["think"] is False
        and chat["options"] == {"temperature": 0.0, "seed": 0}
    )
    assert client.ollama_answers()
    assert "fake-chat" in client.ollama.installed()
    client.ollama.pull("new-model")
    assert state.pulled == ["new-model"]
    assert client.ollama.hardware() == {"loaded_vram": 0}


def test_an_unknown_model_is_an_endpoint_error(ollama: tuple[str, FakeOllamaState]) -> None:
    with pytest.raises(EndpointError, match="404"):
        client_for(ollama[0]).show("missing")


def test_ollama_not_running_says_how_to_fix_it(no_network: list[str]) -> None:
    client = client_for("http://localhost:9")
    assert not client.ollama_answers()
    with pytest.raises(EndpointError, match="could not be reached"):
        client.embed("m", ["x"])


def test_endpoints_by_name_with_the_key_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_KEY", "secret-value")
    with fake_endpoint() as (url, state):
        state.reply = lambda prompt: f"<think>x</think>answer to {prompt}"
        client = client_for("http://localhost:9", {"remote": Endpoint("remote", url, "FAKE_KEY")})
        embedded = client.embed("endpoint:remote/text-embed", ["a", "b"])
        assert len(embedded.vectors) == 2 and embedded.token_counts is None
        assert client.chat(ChatRequest("endpoint:remote/chat", "q")) == "answer to q"
        assert client.rerank("endpoint:remote/rr", "cat food", ["dog", "cat food", "cat"]) == [0.0, 2.0, 1.0]
        assert client.show("endpoint:remote/x").context_length is None
        assert all(headers.get("Authorization") == "Bearer secret-value" for _, _, headers in state.requests)


def test_endpoint_errors_and_naming(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FAKE_KEY", raising=False)
    with fake_endpoint(FakeEndpointState(status=400)) as (url, _):
        client = client_for(
            "http://localhost:9",
            {"remote": Endpoint("remote", url, None), "keyed": Endpoint("keyed", url, "FAKE_KEY")},
        )
        with pytest.raises(EndpointError, match="answered 400"):
            client.embed("endpoint:remote/m", ["a"])
        with pytest.raises(ConfigError, match=r"\$FAKE_KEY, which is not set"):
            client.embed("endpoint:keyed/m", ["a"])
    with pytest.raises(ConfigError, match="names no configured endpoint"):
        client.embed("endpoint:nowhere/m", ["a"])
    with pytest.raises(ConfigError, match="Ollama has no rerank route"):
        client.rerank("gemma4", "q", ["a"])


def test_retries_on_server_errors_then_gives_up() -> None:
    waits: list[float] = []
    with fake_endpoint(FakeEndpointState(status=503)) as (url, state):
        with pytest.raises(EndpointError, match="answered 503") as caught:
            request_json(f"{url}/embeddings", {"input": []}, sleep=waits.append)
        assert caught.value.retryable
        assert waits == [1.0, 2.0, 4.0] and len(state.requests) == 4


def test_only_http_addresses() -> None:
    with pytest.raises(EndpointError, match="not an http"):
        request_json("file:///etc/passwd")


def test_missing_counts_are_unknown_not_zero(
    ollama: tuple[str, FakeOllamaState], monkeypatch: pytest.MonkeyPatch
) -> None:
    url, _ = ollama
    from ragcourt.io import ollama as dialect

    real = dialect.request_json

    def without_counts(address: str, body: object = None, **kwargs: object):  # type: ignore[no-untyped-def]
        reply = real(address, body, **kwargs)  # type: ignore[arg-type]
        reply.pop("prompt_eval_count", None)
        return reply

    monkeypatch.setattr(dialect, "request_json", without_counts)
    assert client_for(url).embed("fake-embed", ["one two"]).token_counts is None
