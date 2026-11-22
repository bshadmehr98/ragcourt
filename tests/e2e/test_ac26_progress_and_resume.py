"""Guarantee 26: a long run shows progress and resumes (design §10.4, §16).

The default suite interrupts a scripted run part-way; ``tests/real/`` does the same with real models.
"""

import shutil
from pathlib import Path

import pytest

from ragcourt.flows.evaluate import Evaluator
from ragcourt.testing import FakeOllamaState
from tests.conftest import Run, results_of


def test_an_interrupted_run_resumes_to_the_same_results(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, state = rank_project
    code, out, _ = run("rank", corpus, "--yes")
    assert code == 0 and "kept" in out and "done" in out  # progress per category
    uninterrupted = results_of(project)
    shutil.rmtree(project / ".ragcourt" / "runs")
    real = Evaluator.evaluate
    calls = {"count": 0}

    def stop_after_three(self: Evaluator, spec):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        if calls["count"] > 3:
            raise KeyboardInterrupt
        return real(self, spec)

    monkeypatch.setattr(Evaluator, "evaluate", stop_after_three)
    code, _, err = run("rank", corpus, "--yes")
    assert code == 130 and "--resume" in err
    progress = next((project / ".ragcourt" / "runs").glob("*/progress.jsonl")).read_text()
    assert '"step": "embedder"' in progress
    monkeypatch.setattr(Evaluator, "evaluate", real)
    before = len(state.requests)
    code, out, _ = run("rank", corpus, "--yes", "--resume")
    assert code == 0 and "Reusing" in out
    resumed = results_of(project)
    for data in (uninterrupted, resumed):
        # The plan and estimate say whether questions were still to write; everything measured must match.
        for key in ("run", "time_minutes", "plan", "estimate"):
            data.pop(key)
        for config in data["configurations"]:
            for key in ("latency_ms_p50", "latency_ms_p95", "index_ms"):
                config["costs"].pop(key)
    assert resumed == uninterrupted
    assert len(list((project / ".ragcourt" / "runs").glob("*"))) == 1  # the same run folder, finished
    assert len(state.requests) >= before
