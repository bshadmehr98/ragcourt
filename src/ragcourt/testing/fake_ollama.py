"""A fake Ollama server on a free local port, for integration tests (design §15.2).

It answers the routes the ``ollama`` dialect uses: ``/api/tags``, ``/api/show``, ``/api/embed`` (vectors from
the ``FakeEmbedder``, the text cut at the model's context length and counted like Ollama, one count per
call), ``/api/chat`` (replies from a function of the prompt), ``/api/pull`` and ``/api/ps``. It records every
request. It runs in a background thread because a test must talk to it while it serves; ragcourt's own
code stays sequential.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from ragcourt.testing.fake_embedder import FakeEmbedder, fake_tokens

Reply = Callable[[str], str]


@dataclass
class FakeOllamaState:
    """The models the fake has, how it replies to chat, and what it was asked."""

    models: dict[str, int] = field(default_factory=lambda: {"fake-embed": 64, "fake-chat": 4096})
    reply: Reply = field(default=lambda _prompt: "{}")
    requests: list[tuple[str, dict[str, Any]]] = field(default_factory=list[tuple[str, dict[str, Any]]])
    pulled: list[str] = field(default_factory=list[str])
    embedder: FakeEmbedder = field(default_factory=lambda: FakeEmbedder(max_tokens=None))


class _Handler(BaseHTTPRequestHandler):
    """Answers one request from the shared state (D-038: http.server works only by subclassing)."""

    state: FakeOllamaState

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet: tests read ``state.requests`` instead."""

    def do_GET(self) -> None:
        """``/api/tags`` and ``/api/ps``."""
        self.state.requests.append((self.path, {}))
        if self.path == "/api/tags":
            models = [
                {"name": f"{name}:latest", "size": 1000, "digest": f"sha-{name}"}
                for name in self.state.models
            ]
            self._send({"models": models})
        elif self.path == "/api/ps":
            self._send({"models": []})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self) -> None:
        """``/api/show``, ``/api/embed``, ``/api/chat`` and ``/api/pull``."""
        length = int(self.headers.get("Content-Length", "0"))
        body: dict[str, Any] = json.loads(self.rfile.read(length) or b"{}")
        self.state.requests.append((self.path, body))
        model = str(body.get("model", "")).removesuffix(":latest")
        if self.path == "/api/pull":
            self.state.pulled.append(model)
            self.state.models[model] = 2048
            self._send_lines([{"status": "pulling"}, {"status": "success"}])
        elif model not in self.state.models:
            self._send({"error": f"model '{model}' not found"}, 404)
        elif self.path == "/api/show":
            self._send({"model_info": {"fake.context_length": self.state.models[model]}})
        elif self.path == "/api/embed":
            self._send(self._embed(model, body))
        elif self.path == "/api/chat":
            content = self.state.reply(str(body["messages"][-1]["content"]))
            self._send({"message": {"role": "assistant", "content": content}})
        else:
            self._send({"error": "not found"}, 404)

    def _embed(self, model: str, body: dict[str, Any]) -> dict[str, Any]:
        limit = int(body.get("options", {}).get("num_ctx") or self.state.models[model])
        texts = [" ".join(fake_tokens(text)[:limit]) for text in body["input"]]
        embedded = self.state.embedder.embed(texts)
        counts = embedded.token_counts or []
        return {"embeddings": embedded.vectors, "prompt_eval_count": sum(counts)}

    def _send(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_lines(self, lines: list[dict[str, Any]]) -> None:
        data = b"".join(json.dumps(line).encode() + b"\n" for line in lines)
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@contextmanager
def fake_ollama(state: FakeOllamaState | None = None) -> Generator[tuple[str, FakeOllamaState]]:
    """Serve a fake Ollama on ``127.0.0.1``; yields its URL and its state."""
    shared = state or FakeOllamaState()
    handler = type("Handler", (_Handler,), {"state": shared})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}", shared
    finally:
        server.shutdown()
        server.server_close()
