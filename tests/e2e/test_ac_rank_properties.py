"""Guarantees 6, 10, 11, 15, 16, 21 and 23: properties of ranking runs (design §16)."""

import json
import re
import shutil
from pathlib import Path

import pytest

from ragcourt.core.metrics import Ranking, all_metrics
from ragcourt.core.relevance import token_map
from ragcourt.testing import FakeOllamaState
from ragcourt.types import Chunk
from ragcourt.types.questions import Question
from tests.conftest import Run, results_of


def embed_calls(state: FakeOllamaState) -> int:
    return sum(len(body["input"]) for path, body in state.requests if path == "/api/embed")


def test_ac6_gold_is_independent_of_chunking(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    assert run("rank", corpus, "--yes", "--chunkers", "fixed:size=60,overlap=0")[0] == 0
    before = (project / ".ragcourt" / "questions.jsonl").read_text()
    assert run("rank", corpus, "--yes", "--chunkers", "markdown:size=300,overlap=0;sentence:size=100")[0] == 0
    assert (project / ".ragcourt" / "questions.jsonl").read_text() == before


def test_ac10_metrics_equal_their_hand_worked_values() -> None:
    text = "a b c d e f g h i j"
    question = Question("q", "Q?", "keyword", "d.md", 4, 9, "c d e")
    chunks = [
        Chunk("d.md", 0, 0, 5, "a b c"),
        Chunk("d.md", 1, 4, 11, "c d e f"),
        Chunk("d.md", 2, 12, 19, "g h i j"),
    ]
    metrics = all_metrics(Ranking(question, chunks, chunks, 2, 4), token_map({"d.md": text}))
    assert metrics["hit_at_k"] == 1.0 and metrics["mrr"] == 0.5 and metrics["recall_at_k"] == 1.0
    assert metrics["token_precision_at_k"] == pytest.approx(0.5) and metrics[
        "recall_at_budget"
    ] == pytest.approx(2 / 3)


WHOLE_QUOTES = [
    ("How long is the first retry delay?", "The first retry waits 10 seconds"),
    ("What is the default job timeout?", "The default timeout is 300 seconds"),
    ("Are job arguments logged?", "Job\narguments are never logged"),
    ("Does Larkspur work with MySQL?", "No. Larkspur depends on two features of PostgreSQL"),
    ("What does the drain timeout set?", "sets how long it waits"),
    ("Can the dashboard be public?", "It must not be exposed to the internet"),
]


def test_ac11_size_cannot_win(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None, tmp_path: Path
) -> None:
    project, _ = rank_project
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("retries.md", "timeouts.md", "security.md", "faq.txt"):
        (docs / name).write_text((corpus / name).read_text())
    mine = tmp_path / "mine.jsonl"
    mine.write_text("".join(json.dumps({"question": q, "quote": a}) + "\n" for q, a in WHOLE_QUOTES))
    (project / "ragcourt_stages").mkdir()
    (project / "ragcourt_stages" / "whole.py").write_text(
        "from ragcourt.stages import chunker\n\n@chunker('whole')\ndef whole(text):\n    return [text]\n"
    )
    code, _, err = run(
        "rank",
        docs,
        "--yes",
        "--questions",
        "0",
        "--questions-file",
        mine,
        "--embedders",
        "fake",
        "--chunkers",
        "whole;sentence:size=60",
    )
    assert code == 0, err
    configs = {
        c["spec"]["chunker"]: c["held_out"]
        for c in results_of(project)["configurations"]
        if c["spec"]["retriever"] == "dense" and c["spec"]["reranker"] == "none"
    }
    assert configs["whole"]["recall_at_k"] == 1.0  # four whole documents: every quote is in the top 5
    assert configs["whole"]["recall_at_budget"] < configs["sentence:size=60"]["recall_at_budget"]


def test_ac15_the_cache_works(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, tmp_path: Path
) -> None:
    _project, state = rank_project
    assert run("rank", corpus, "--yes")[0] == 0
    first = embed_calls(state)
    assert run("rank", corpus, "--yes")[0] == 0
    assert embed_calls(state) - first == 0
    copy = tmp_path / "docs"
    copy.mkdir()
    for path in corpus.iterdir():
        (copy / path.name).write_text(path.read_text())
    (copy / "faq.txt").write_text(
        (corpus / "faq.txt").read_text() + "\nWhy is the sky blue?\nBecause of scattering.\n"
    )
    before = embed_calls(state)
    assert run("rank", copy, "--yes")[0] == 0
    assert 0 < embed_calls(state) - before < first / 3


def test_ac16_the_budget_holds(rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run) -> None:
    project, state = rank_project
    code, out, err = run("rank", corpus, "--yes", "--budget-minutes", "0.0001")
    assert code == 4 and "over the budget" in err and "Plan" in out
    assert state.requests == []
    assert not (project / ".ragcourt" / "runs").exists() or not list(
        (project / ".ragcourt" / "runs").glob("*/results.json")
    )


def test_ac21_two_runs_give_the_same_results(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    runs = []
    for _ in range(2):
        shutil.rmtree(project / ".ragcourt", ignore_errors=True)
        assert run("rank", corpus, "--yes")[0] == 0
        data = results_of(project)
        for key in ("run", "time_minutes"):
            data.pop(key)
        for config in data["configurations"]:
            for key in ("latency_ms_p50", "latency_ms_p95", "index_ms"):
                config["costs"].pop(key)
        runs.append(data)
    assert runs[0] == runs[1]


def test_ac23_the_report_is_self_contained(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    project, _ = rank_project
    code, out, _ = run("rank", corpus, "--yes", "--html")
    assert code == 0
    report = Path(out.strip().splitlines()[-1].removeprefix("Report: ")).read_text()
    assert (
        not re.search(r"(src|href)=['\"]?https?:", report)
        and "http://" not in report
        and "https://" not in report
    )
    results = results_of(project)
    for board in results["boards"]:
        for row in board["rows"]:
            assert row["label"].replace("|", "").split()[0] in report
            assert (
                f"{row['overall']['mean']:.2f} [{row['overall']['low']:.2f}, {row['overall']['high']:.2f}]"
                in report
            )
    for blame in results["blames"]:
        assert json.dumps(blame["text"])[1:-1].split("'")[0][:20] in report or blame["text"][:10] in report
