"""Real models through the local Ollama (marker ``real_model``; run by hand, see real-model-tests).

Guarantee 26 with real models, the judge's self-test, measured token counts and the cache. They assert what
holds for any good model, never exact text or scores.
"""

import json
import os
import shutil
import time
import urllib.request
from pathlib import Path

import pytest

from ragcourt.cli import main
from ragcourt.flows.evaluate import Evaluator
from ragcourt.testing import corpus_path

pytestmark = [pytest.mark.real_model, pytest.mark.slow]
OLLAMA = os.environ.get("RAGCOURT_TEST_BASE_URL", "http://localhost:11434")
CHAT = os.environ.get("RAGCOURT_TEST_CHAT_MODEL", "gemma4")
EMBED = os.environ.get("RAGCOURT_TEST_EMBED_MODEL", "nomic-embed-text")


def installed() -> set[str]:
    try:
        with urllib.request.urlopen(f"{OLLAMA}/api/tags", timeout=5) as reply:  # noqa: S310 (a local test server)
            names = [model["name"] for model in json.loads(reply.read())["models"]]
    except OSError:
        return set()
    return {name.removesuffix(":latest") for name in names}


@pytest.fixture
def real_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    models = installed()
    if not models:
        pytest.skip(f"Ollama does not answer at {OLLAMA}")
    if CHAT not in models or EMBED not in models:
        pytest.skip(f"needs {CHAT} and {EMBED} in Ollama (ollama pull them)")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "ragcourt.toml").write_text(
        f'ollama_url = "{OLLAMA}"\n[models]\nwriter = "{CHAT}"\njudge = "{CHAT}"\nembedders = ["{EMBED}"]\n'
        f'reranker = "{CHAT}"\n[questions]\nper_category = 4\nmin_held_out = 2\n[search]\nrerankers = ["none"]\n'
        'chunkers = ["recursive:size=256,overlap=32", "markdown:size=512,overlap=64"]\nresamples = 300\n'
    )
    return tmp_path


def results(project: Path) -> dict:  # type: ignore[type-arg]
    data = json.loads(next((project / ".ragcourt" / "runs").glob("*/results.json")).read_text())
    for key in ("run", "time_minutes", "plan", "estimate"):
        data.pop(key)
    for config in data["configurations"]:
        for key in ("latency_ms_p50", "latency_ms_p95", "index_ms"):
            config["costs"].pop(key)
    return data


def test_a_real_run_shows_progress_and_resumes_to_the_same_results(
    real_project: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    time.monotonic()
    assert main(["rank", str(corpus_path()), "--yes"]) == 0
    out = capsys.readouterr().out
    assert "Plan" in out and "kept" in out and "Judge self-test" in out
    full = results(real_project)
    for board in full["boards"]:
        assert all(
            row["overall"]["low"] <= row["overall"]["mean"] <= row["overall"]["high"] for row in board["rows"]
        )
    shutil.rmtree(real_project / ".ragcourt" / "runs")
    real = Evaluator.evaluate
    count = {"calls": 0}

    def interrupted(self: Evaluator, spec):  # type: ignore[no-untyped-def]
        count["calls"] += 1
        if count["calls"] > 2:
            raise KeyboardInterrupt
        return real(self, spec)

    monkeypatch.setattr(Evaluator, "evaluate", interrupted)
    assert main(["rank", str(corpus_path()), "--yes"]) == 130
    monkeypatch.setattr(Evaluator, "evaluate", real)
    assert main(["rank", str(corpus_path()), "--yes", "--resume"]) == 0
    assert results(real_project) == full


def test_real_token_counts_are_measured(real_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["audit", str(corpus_path()), "--chunker", "markdown", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["sizes"] == "measured" and data["limit"]


def test_the_judge_passes_its_self_test(real_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["models", "test", "judge"]) == 0
    assert "passed" in capsys.readouterr().out
