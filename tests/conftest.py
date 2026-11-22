"""Shared fixtures. The default suite is offline and deterministic: no network and no real model
(CONTRIBUTING.md, "Tests"). Local fake servers on 127.0.0.1 stand in for Ollama and endpoints."""

from __future__ import annotations

import socket
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

from ragcourt import stages
from ragcourt.cli import main
from ragcourt.testing import FakeOllamaState, ScriptedReplies, corpus_path, fake_ollama, register_fakes

stages.load_builtins()
register_fakes()

Run = Callable[..., tuple[int, str, str]]


def audit_findings(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Every finding of every chunker in an ``audit --json`` result."""
    found: list[dict[str, Any]] = []
    for result in data["chunkers"]:
        found += result["findings"]
    return found


@pytest.fixture
def registry() -> Iterator[None]:
    """Restore the stage registry, and forget the user modules, after a test that registers stages."""
    saved = {kind: dict(entries) for kind, entries in stages._REGISTRY.items()}
    yield
    for kind, entries in saved.items():
        stages._REGISTRY[kind] = entries
    for name in list(sys.modules):
        if name == "ragcourt_stages" or name.startswith("ragcourt_stages."):
            del sys.modules[name]


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty project folder as the current directory."""
    folder = tmp_path / "project"
    folder.mkdir()
    monkeypatch.chdir(folder)
    return folder


@pytest.fixture
def corpus() -> Path:
    """The bundled corpus."""
    return corpus_path()


@pytest.fixture
def run(capsys: pytest.CaptureFixture[str]) -> Run:
    """Run ``ragcourt`` in-process; returns the exit code, stdout and stderr."""

    def invoke(*args: str) -> tuple[int, str, str]:
        code = main([str(arg) for arg in args])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return invoke


@pytest.fixture
def ollama() -> Iterator[tuple[str, FakeOllamaState]]:
    """A fake Ollama server; yields its URL and state."""
    with fake_ollama() as served:
        yield served


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Block every outgoing connection; returns the addresses that were tried."""
    tried: list[str] = []

    def refuse(self: socket.socket, address: object) -> None:
        tried.append(str(address))
        raise ConnectionRefusedError("network blocked by the test")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    return tried


SCRIPTED_TOML = """ollama_url = "{url}"
[models]
writer = "fake-chat"
judge = "fake-chat"
embedders = ["fake-embed"]
reranker = "fake-chat"
doctor = "fake-chat"
[questions]
per_category = {per_category}
min_held_out = 2
"""


@pytest.fixture
def scripted(project: Path, ollama: tuple[str, FakeOllamaState]) -> ScriptedReplies:
    """A project whose models are a fake Ollama answering with ``ScriptedReplies`` (edit it in the test)."""
    url, state = ollama
    replies = ScriptedReplies()
    state.reply = replies
    (project / "ragcourt.toml").write_text(SCRIPTED_TOML.format(url=url, per_category=3))
    return replies
