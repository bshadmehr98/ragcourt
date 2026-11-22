"""Guarantee 19: nothing leaves without an endpoint (design §11.2, §16)."""

import socket
from pathlib import Path
from typing import Any

import pytest

from ragcourt.testing import FakeOllamaState, fake_endpoint
from tests.conftest import Run


@pytest.fixture
def contacted(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every host a connection was opened to."""
    hosts: list[str] = []
    real = socket.socket.connect

    def connect(self: socket.socket, address: Any) -> object:
        hosts.append(str(address[0]) if isinstance(address, tuple) else str(address))
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    return hosts


def test_only_the_local_ollama_with_no_endpoint(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, contacted: list[str]
) -> None:
    for command in (
        ["audit", corpus],
        ["questions", corpus],
        ["rank", corpus, "--yes"],
        ["models"],
        ["explain"],
    ):
        assert run(*command)[0] == 0
    assert set(contacted) == {"127.0.0.1"}


def test_only_the_endpoint_and_ollama_and_no_key_written(
    rank_project: tuple[Path, FakeOllamaState],
    corpus: Path,
    run: Run,
    contacted: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project, _ = rank_project
    monkeypatch.setenv("RC_TEST_KEY", "sk-very-secret-value")
    with fake_endpoint() as (url, state):
        text = (
            (project / "ragcourt.toml")
            .read_text()
            .replace(
                'embedders = ["fake-embed", "fake"]', 'embedders = ["endpoint:remote/text-embed", "fake"]'
            )
        )
        (project / "ragcourt.toml").write_text(
            text + f'\n[endpoints.remote]\nbase_url = "{url}"\napi_key_env = "RC_TEST_KEY"\n'
        )
        code, out, err = run("rank", corpus, "--yes")
        assert code == 0, err
        assert any(
            headers.get("Authorization") == "Bearer sk-very-secret-value" for _, _, headers in state.requests
        )
    assert set(contacted) == {"127.0.0.1"}
    for path in (project / ".ragcourt").rglob("*"):
        if path.is_file():
            assert b"sk-very-secret-value" not in path.read_bytes(), path
    assert "sk-very-secret-value" not in out + err
