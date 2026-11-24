"""Guarantee 42: the misses of your own pipeline are blamed as far as code can see (§16, change 0006)."""

from pathlib import Path

import pytest

from ragcourt.testing import FakeOllamaState
from tests.conftest import Run, results_of
from tests.e2e.test_ac41_your_pipeline import TWIN, write_pipeline


@pytest.mark.parametrize("listed", [True, False])
def test_ac42_every_miss_has_one_cause_as_far_as_code_can_see(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None, listed: bool
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=listed)
    assert run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search")[0] == 0
    results = results_of(project)
    misses = [key for key, ranks in results["held_out_ranks"].items() if ranks["hit_at_k"] < 1]
    blames = results["blames"]
    assert misses and sorted(blame["question"] for blame in blames) == sorted(misses)
    allowed = {"retrieval", "ranking"} | ({"chunker"} if listed else set())
    assert {blame["stage"] for blame in blames} <= allowed
    assert all(blame["level"] == "indicated" and "--no-search" in blame["fix"] for blame in blames)
    if listed:  # 60-token chunks cut quotes: with the chunks known that is the chunker's doing
        assert any(blame["mechanism"] == "chunker.split" for blame in blames)
    else:
        assert all("register pipeline_chunks" in b["evidence"] for b in blames if b["stage"] == "retrieval")
    overall = results["ceilings"]["overall"]
    assert overall["chunker"] >= overall["retrieval"] >= overall["hit_at_k"]


def test_ac42_a_miss_is_confirmed_only_when_a_measured_pipeline_finds_it(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=True)
    assert run("rank", corpus, "--yes", "--pipeline", "mine")[0] == 0
    results = results_of(project)
    measured = {item["label"] for item in results["configurations"]} - {"your pipeline mine"}
    assert {blame["level"] for blame in results["blames"]} == {"confirmed", "indicated"}
    for blame in results["blames"]:
        named = [label for label in measured if f": {label} reaches the top k" in blame["fix"]]
        assert bool(named) == (blame["level"] == "confirmed"), blame["fix"]
        if blame["level"] == "indicated":
            assert f"none of the {len(measured)} pipelines measured here finds it" in blame["fix"]


def test_ac42_the_same_system_under_another_name_confirms_nothing(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=True)
    flags = ["--embedders", "fake", "--chunkers", "fixed:size=60,overlap=0", "--retrievers", "bm25"]
    assert run("rank", corpus, "--yes", "--pipeline", "mine", *flags, "--rerankers", "none")[0] == 0
    results = results_of(project)
    twin_hits = {key for key, ranks in results["held_out_ranks"].items() if ranks["hit_at_k"] == 1}
    confirmed = [blame for blame in results["blames"] if blame["level"] == "confirmed"]
    # only the dense pipeline of the first step can find what the twin misses; the twin itself never does
    assert all(TWIN not in blame["fix"] for blame in confirmed)
    assert not twin_hits & {blame["question"] for blame in results["blames"]}
