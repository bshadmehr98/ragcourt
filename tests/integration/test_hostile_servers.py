"""A server that redirects, answers too much or answers in the wrong shape (D-057)."""

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from ragcourt import EndpointError
from ragcourt.io import http
from ragcourt.io.client import Client
from ragcourt.types import ChatRequest
from ragcourt.types.config import Config, Endpoint

SEEN: list[dict[str, str]] = []


class _Scripted(BaseHTTPRequestHandler):
    """Answers every request with the class's ``status``, ``headers`` and ``body`` (http.server needs a class)."""

    status = 200
    headers_out: dict[str, str] = {}  # noqa: RUF012 (set per server in the test)
    body = b"{}"

    def log_message(self, format: str, *args: Any) -> None:
        """Quiet."""

    def _answer(self) -> None:
        SEEN.append(dict(self.headers.items()))
        self.send_response(self.status)
        for name, value in self.headers_out.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def do_GET(self) -> None:
        """Every route."""
        self._answer()

    def do_POST(self) -> None:
        """Every route."""
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        self._answer()


@contextmanager
def server(status: int = 200, headers: dict[str, str] | None = None, body: bytes = b"{}") -> Iterator[str]:
    handler = type("Handler", (_Scripted,), {"status": status, "headers_out": headers or {}, "body": body})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()


def test_a_redirect_is_refused_so_the_key_never_reaches_another_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEY", "sk-secret")
    SEEN.clear()
    with server() as elsewhere, server(302, {"Location": f"{elsewhere}/steal"}) as endpoint:
        client = Client(Config(project=Path(), endpoints={"e": Endpoint("e", endpoint, "KEY")}))
        with pytest.raises(EndpointError, match="does not follow redirects"):
            client.chat(ChatRequest("endpoint:e/chat", "q"))
    assert len(SEEN) == 1  # the endpoint only: nothing reached the address it redirected to


def test_an_oversized_or_misshapen_reply_is_one_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http, "MAX_REPLY_BYTES", 100)
    with (
        server(body=json.dumps({"pad": "x" * 500}).encode()) as url,
        pytest.raises(EndpointError, match="more than"),
    ):
        http.request_json(url)
    with server(body=b'{"choices": []}') as url:
        client = Client(Config(project=Path(), endpoints={"e": Endpoint("e", url)}))
        with pytest.raises(EndpointError, match="unexpected shape"):
            client.chat(ChatRequest("endpoint:e/chat", "q"))
