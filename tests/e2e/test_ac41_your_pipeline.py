"""Guarantee 41: your own pipeline is scored like any other (design §16, change 0006)."""

from pathlib import Path

import pytest

from ragcourt.testing import FakeOllamaState
from tests.conftest import Run, results_of

# A pipeline of the user's own that is, inside, ragcourt's fixed chunker with BM25: its numbers must equal
# those of the built-in pipeline `fixed:size=60,overlap=0 | - | bm25 | none`.
MINE = """
from pathlib import Path

from ragcourt import load_documents, stages
from ragcourt.stages import pipeline{extra_import}

CORPUS = load_documents(Path({corpus!r}))
CHUNKS = []
for document in CORPUS.documents:
    CHUNKS += stages.find("chunker", "fixed").function(document.text, size=60, overlap=0)
SEARCH = stages.find("retriever", "bm25").function(CHUNKS, None, None)


@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    return [CHUNKS[index] for index, _ in SEARCH(query, depth)]
{chunks}
"""
LISTED = """

@pipeline_chunks("mine")
def mine_chunks() -> list[str]:
    return CHUNKS
"""
TWIN = "fixed:size=60,overlap=0 | - | bm25 | none"


def write_pipeline(project: Path, corpus: Path, *, listed: bool) -> None:
    (project / "ragcourt_stages").mkdir()
    text = MINE.format(
        corpus=str(corpus),
        extra_import=", pipeline_chunks" if listed else "",
        chunks=LISTED if listed else "",
    )
    (project / "ragcourt_stages" / "mine.py").write_text(text)


def saved_results(project: Path) -> list[dict]:  # type: ignore[type-arg]
    """Every question's result of the user's pipeline, from the run folder."""
    import json

    found = []
    for path in (project / ".ragcourt" / "runs").glob("*/configs/*.json"):
        data = json.loads(path.read_text())
        if data["spec"]["pipeline"]:
            found += list(data["results"].values())
    return found


def config(results: dict, label: str) -> dict:  # type: ignore[type-arg]
    return next(item for item in results["configurations"] if item["label"] == label)


def test_ac41_your_pipeline_gets_the_numbers_of_the_same_built_in_pipeline(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=True)
    flags = ["--chunkers", "fixed:size=60,overlap=0", "--retrievers", "bm25", "--rerankers", "none"]
    code, out, err = run("rank", corpus, "--yes", "--pipeline", "mine", *flags)
    assert code == 0, err
    results = results_of(project)
    assert results["search_chosen"] == TWIN and results["chosen"] == "your pipeline mine"
    assert config(results, "your pipeline mine")["held_out"] == config(results, TWIN)["held_out"]
    assert [step["step"] for step in results["steps"]][-1] == "pipeline"
    last = results["boards"][-1]
    assert last["stage"] == "pipeline" and {row["label"] for row in last["rows"]} == {
        "your pipeline mine",
        TWIN,
    }
    assert last["winner"] is None  # the same numbers: no significant difference
    assert "Step 1 of 4" in out
    assert "your pipeline" in out.split("Step 1 of 4")[0]  # the plan names it before anything is called
    assert "Your pipeline mine is called once per question with the question's text" in out
    assert "chunk texts of mine were found in your documents" in out and "Your pipeline" in out


def test_ac41_no_search_calls_no_embedding_model(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, state = rank_project
    write_pipeline(project, corpus, listed=False)
    code, out, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search", "--html")
    assert code == 0, err
    assert not [request for request in state.requests if "embed" in request[0]]
    results = results_of(project)
    assert [step["step"] for step in results["steps"]] == ["pipeline"]
    assert results["pipeline"]["chunks_known"] is False and results["search_chosen"] is None
    assert "2. embedders" not in out and "2. your pipeline" in out
    assert "Your pipeline alone" in out and "Winner:" not in out
    assert [role["role"] for role in results["plan"]["roles"]] == ["writer", "judge"]
    assert "nDCG is measured against a chunk that holds the whole quote" in out
    report = next((project / ".ragcourt" / "runs").glob("*/report.html")).read_text()
    assert "Your pipeline: <b>your pipeline mine</b>" in report and "Your pipeline alone" in report
    code, explained, _ = run("explain")
    assert code == 0 and "Run " in explained and "your pipeline mine" in explained and "cause:" in explained


def test_ac41_texts_that_are_not_text_of_the_documents_are_counted_and_score_nothing(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=False)
    path = project / "ragcourt_stages" / "mine.py"
    path.write_text(
        path.read_text().replace(
            "return [CHUNKS[index] for index, _ in SEARCH(query, depth)]",
            "return ['Summary: a title my system added.'] + [CHUNKS[i] for i, _ in SEARCH(query, depth)]",
        )
    )
    code, out, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search")
    assert code == 0, err
    assert results_of(project)["pipeline"]["not_found"] == 1
    assert "1 are not text of your documents" in out and "count against precision" in out


def test_ac41_a_text_at_the_top_that_is_not_of_the_documents_scores_nothing(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=False)
    path = project / "ragcourt_stages" / "mine.py"
    path.write_text(
        path.read_text().replace(
            "return [CHUNKS[index] for index, _ in SEARCH(query, depth)]",
            "return ['Summary: a title my system added.', 'Edit this page on the Larkspur wiki · "
            "Larkspur contributors'] + [CHUNKS[i] for i, _ in SEARCH(query, depth)] * 2",
        )
    )
    code, out, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search", "--k", "1")
    assert code == 0, err
    results = results_of(project)
    assert results["pipeline"]["not_found"] == 1 and results["pipeline"]["several"] >= 1
    assert f"{results['pipeline']['several']} are found in more than one place" in out
    assert config(results, "your pipeline mine")["held_out"]["hit_at_k"] == 0.0  # the top text holds no quote
    ranks = [len(item["retrieved"]) for item in saved_results(project)]
    assert max(ranks) <= 50  # cut at the depth, repeats left out


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("raise RuntimeError('database down')", "Your pipeline 'mine' failed for the question"),
        ("return 'one string'", "must return a list of strings"),
        ("return [1, 2]", "must return a list of strings"),
    ],
)
def test_a_pipeline_that_fails_or_returns_something_else_is_one_message(
    rank_project: tuple[Path, FakeOllamaState],
    corpus: Path,
    run: Run,
    registry: None,
    body: str,
    message: str,
) -> None:
    project, _ = rank_project
    (project / "ragcourt_stages").mkdir()
    code_text = (
        f"from ragcourt.stages import pipeline\n\n@pipeline('mine')\ndef mine(query, depth):\n    {body}\n"
    )
    (project / "ragcourt_stages" / "mine.py").write_text(code_text)
    code, _, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search")
    assert code == 1 and message in err and "Traceback" not in err


def test_a_pipeline_that_returns_nothing_from_the_documents_is_refused(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    (project / "ragcourt_stages").mkdir()
    (project / "ragcourt_stages" / "mine.py").write_text(
        "from ragcourt.stages import pipeline\n\n@pipeline('mine')\ndef mine(query, depth):\n    return ['zzqx vvkw']\n"
    )
    code, _, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search")
    assert code == 1 and "is text of the documents" in err


@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--no-search"], "name your pipeline with --pipeline"),
        (["--pipeline", "nope"], "No pipeline is named 'nope'"),
        (["--pipeline", "nope", "--no-search", "--chunkers", "fixed"], "No pipeline is named 'nope'"),
    ],
)
def test_wrong_flags_are_one_message_before_the_plan(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, flags: list[str], message: str
) -> None:
    code, out, err = run("rank", corpus, "--yes", *flags)
    assert code == 1 and message in err and "Plan" not in out


def test_no_search_refuses_flags_that_would_do_nothing(
    rank_project: tuple[Path, FakeOllamaState], corpus: Path, run: Run, registry: None
) -> None:
    project, _ = rank_project
    write_pipeline(project, corpus, listed=False)
    code, out, err = run("rank", corpus, "--yes", "--pipeline", "mine", "--no-search", "--chunkers", "fixed")
    assert code == 1 and "have nothing to do" in err and "Plan" not in out
