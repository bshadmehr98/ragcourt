"""Guarantee 27: setup asks before pulling (design §11.3, §16).

``setup`` never downloads a model without the user's yes (or ``--yes``), and shows each model's size first.
"""

from pathlib import Path

import pytest

from ragcourt.testing import FakeOllamaState, ScriptedReplies
from tests.conftest import Run


@pytest.fixture
def bare_ollama(
    project: Path, ollama: tuple[str, FakeOllamaState], monkeypatch: pytest.MonkeyPatch
) -> FakeOllamaState:
    url, state = ollama
    state.models = {}
    state.reply = ScriptedReplies()
    (project / "settings.toml").write_text(f'ollama_url = "{url}"\n')
    monkeypatch.setattr("ragcourt.commands.setup.ram_gb", lambda: 32.0)
    monkeypatch.setattr("ragcourt.commands.setup.gpu_gb", lambda: 8.0)
    return state


def test_no_download_without_yes(project: Path, run: Run, bare_ollama: FakeOllamaState) -> None:
    code, out, _ = run("setup", "--config", "settings.toml")
    assert code == 0 and bare_ollama.pulled == []
    assert "gemma4" in out and "6.60 GB" in out and out.index("6.60 GB") < out.index("Nothing downloaded")
    assert not (project / "ragcourt.toml").exists()


def test_an_answer_of_yes_pulls(
    project: Path, run: Run, bare_ollama: FakeOllamaState, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("ragcourt.io.ask.read_answer", lambda question: "y")
    assert run("setup", "--config", "settings.toml")[0] == 0
    assert "gemma4" in bare_ollama.pulled


def test_yes_pulls_writes_a_commented_config_and_tests_the_judge(
    project: Path, run: Run, bare_ollama: FakeOllamaState
) -> None:
    code, out, _ = run("setup", "--yes", "--config", "settings.toml")
    assert code == 0
    assert sorted(bare_ollama.pulled) == ["embeddinggemma", "gemma4", "mxbai-embed-large", "nomic-embed-text"]
    written = (project / "ragcourt.toml").read_text()
    assert "# judge: drops invalid questions" in written and 'embedders = ["nomic-embed-text"' in written
    assert "Judge self-test: gemma4" in out and "passed" in out
    again = run("setup", "--config", "settings.toml")[1]
    assert "exists; left as it is" in again


def test_without_ollama_it_says_how_to_start_it(project: Path, run: Run, no_network: list[str]) -> None:
    code, out, _ = run("setup")
    assert code == 1 and "Install Ollama" in out
