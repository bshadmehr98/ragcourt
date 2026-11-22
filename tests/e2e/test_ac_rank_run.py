"""Guarantees 9, 12, 13, 14, 17, 28, 32 and 18 (rank): one scripted run, read through its outputs (§16)."""

import json
from pathlib import Path

import pytest

from ragcourt.core.blame import MECHANISM_NAMES
from ragcourt.testing import FakeOllamaState
from tests.conftest import Run, results_of


@pytest.fixture
def ran(rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run) -> tuple[Path, str, dict]:  # type: ignore[type-arg]
    project, _ = rank_project
    code, out, err = run("rank", corpus, "--yes", "--html")
    assert code == 0, err
    return project, out, results_of(project)


def test_ac28_the_plan_comes_before_any_model_call(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run
) -> None:
    _project, state = rank_project
    code, out, _ = run("rank", corpus)  # no --yes and no terminal: the first run is not started
    assert code == 0 and "Not started" in out
    assert state.requests == []  # no model was called
    for words in (
        "Plan",
        "writer",
        "fake-chat",
        "ragcourt.toml",
        "is shown",
        "1. questions",
        "5. rerankers",
        "estimated",
    ):
        assert words in out


def test_ac17_greedy_embedders_first_only_the_listed_configurations(ran: tuple[Path, str, dict]) -> None:  # type: ignore[type-arg]
    _, out, results = ran
    assert [step["step"] for step in results["steps"]] == ["embedder", "chunker", "retriever", "reranker"]
    first = results["steps"][0]["evaluated"]
    assert first == [
        "recursive:size=200,overlap=20 | fake-embed | dense | none",
        "recursive:size=200,overlap=20 | fake | dense | none",
    ]
    evaluated: set[str] = set()
    for step in results["steps"]:
        evaluated |= set(step["evaluated"])
    assert {config["label"] for config in results["configurations"]} == evaluated
    assert len(evaluated) == 2 + 3 + 3 + 2 - 3  # repeats between steps measured once
    assert (
        out.index("Step 1 of 4: embedders")
        < out.index("Step 2 of 4: chunkers")
        < out.index("Step 4 of 4: rerankers")
    )


def test_ac9_and_ac32_leaderboards_are_held_out_and_per_category(ran: tuple[Path, str, dict]) -> None:  # type: ignore[type-arg]
    _, out, results = ran
    for board in results["boards"]:
        for row in board["rows"]:
            assert row["categories"] and {"mean", "low", "high"} <= set(row["overall"])
        assert board["smallest_difference"]
    assert (
        "(recall_at_budget, held-out)" in out and "Smallest difference these questions can tell apart" in out
    )


def test_ac12_ties_are_said(ran: tuple[Path, str, dict]) -> None:  # type: ignore[type-arg]
    _, out, results = ran
    for board in results["boards"]:
        if board["winner"]:
            assert f"Winner: {board['winner']}." in out
        else:
            assert "No significant difference between" in out and any(
                row["tied_with_top"] for row in board["rows"]
            )


def test_ac13_and_ac14_every_miss_has_one_cause_a_level_and_a_fix(ran: tuple[Path, str, dict]) -> None:  # type: ignore[type-arg]
    _, _, results = ran
    misses = [key for key, ranks in results["held_out_ranks"].items() if ranks["hit_at_k"] < 1]
    blamed = [blame["question"] for blame in results["blames"]]
    assert sorted(blamed) == sorted(misses) and len(set(blamed)) == len(blamed)
    for blame in results["blames"]:
        assert blame["mechanism"] in MECHANISM_NAMES and blame["level"] in ("confirmed", "indicated")
        assert blame["fix"] and blame["evidence"] and "«" in blame["context"]
        if blame["level"] == "indicated":
            assert any(
                words in blame["fix"]
                for words in (
                    "not measured",
                    "no tested embedder",
                    "misses the top k there too",
                    "differs too",
                )
            )
    overall = results["ceilings"]["overall"]
    assert overall["chunker"] >= overall["retrieval"] >= overall["hit_at_k"]
    stages = [blame["stage"] for blame in results["blames"]]
    lost = {stage: stages.count(stage) for stage in ("chunker", "embedder", "retriever", "ranking")}
    total = overall["questions"]
    assert overall["chunker"] == pytest.approx(1 - lost["chunker"] / total)
    assert overall["hit_at_k"] == pytest.approx(1 - sum(lost.values()) / total)


def test_explain_and_report_read_the_results(ran: tuple[Path, str, dict], run: Run) -> None:  # type: ignore[type-arg]
    _project, _, results = ran
    code, out, _ = run("explain")
    assert code == 0 and "cause:" in out and "Legend:" in out
    if results["blames"]:
        first = results["blames"][0]["question"]
        shown = run("explain", "--show", first)[1]
        assert "«" in shown and "⟦" in shown
    assert json.loads(run("explain", "--json")[1]) == results["blames"]
    assert run("explain", "--show", "nope")[0] == 1
    code, out, _ = run("report")
    assert code == 0 and Path(out.strip()).is_file()


def test_ac18_a_users_chunker_appears_in_rank(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    (project / "ragcourt_stages").mkdir()
    (project / "ragcourt_stages" / "mine.py").write_text(
        "from ragcourt.stages import chunker\n\n@chunker('by_paragraph')\ndef by_paragraph(text):\n    return [p for p in text.split('\\n\\n') if p.strip()]\n"
    )
    code, _, err = run("rank", corpus, "--yes", "--chunkers", "by_paragraph;fixed:size=60,overlap=0")
    assert code == 0, err
    assert any(
        config["spec"]["chunker"] == "by_paragraph" for config in results_of(project)["configurations"]
    )
