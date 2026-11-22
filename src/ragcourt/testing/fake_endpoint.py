"""A fake OpenAI-compatible endpoint on a free local port, for integration tests (design §15.2).

``/embeddings`` (vectors from the ``FakeEmbedder``), ``/chat/completions`` (replies from a function of the
prompt) and ``/rerank`` (scores by shared words). It records each request with its headers, so tests can
check which key was sent.
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


@dataclass
class FakeEndpointState:
    """How the fake replies, and what it was asked."""

    reply: Callable[[str], str] = field(default=lambda _prompt: "{}")
    requests: list[tuple[str, dict[str, Any], dict[str, str]]] = field(
        default_factory=list[tuple[str, dict[str, Any], dict[str, str]]]
    )
    status: int = 200


class _Handler(BaseHTTPRequestHandler):
    """Answers one request (D-038: http.server works only by subclassing)."""

    state: FakeEndpointState

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet."""

    def do_POST(self) -> None:
        """The three routes."""
        length = int(self.headers.get("Content-Length", "0"))
        body: dict[str, Any] = json.loads(self.rfile.read(length) or b"{}")
        self.state.requests.append((self.path, body, dict(self.headers.items())))
        if self.state.status != 200:
            self._send({"error": "scripted failure"}, self.state.status)
        elif self.path.endswith("/embeddings"):
            vectors = FakeEmbedder().embed(list(body["input"])).vectors
            data = [{"index": number, "embedding": vector} for number, vector in enumerate(vectors)]
            self._send({"data": list(reversed(data)), "usage": {"prompt_tokens": 0}})
        elif self.path.endswith("/chat/completions"):
            content = self.state.reply(str(body["messages"][-1]["content"]))
            self._send({"choices": [{"message": {"role": "assistant", "content": content}}]})
        elif self.path.endswith("/rerank"):
            query = set(fake_tokens(str(body["query"])))
            scores = [len(query & set(fake_tokens(str(document)))) for document in body["documents"]]
            results = [
                {"index": number, "relevance_score": float(score)} for number, score in enumerate(scores)
            ]
            self._send({"results": results})
        else:
            self._send({"error": "not found"}, 404)

    def _send(self, payload: dict[str, Any], status: int = 200) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@contextmanager
def fake_endpoint(state: FakeEndpointState | None = None) -> Generator[tuple[str, FakeEndpointState]]:
    """Serve a fake endpoint on ``127.0.0.1``; yields its base URL (with ``/v1``) and its state."""
    shared = state or FakeEndpointState()
    handler = type("Handler", (_Handler,), {"state": shared})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1", shared
    finally:
        server.shutdown()
        server.server_close()
