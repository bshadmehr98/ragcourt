"""Guarantee 4: sizes are labelled (design §4.3, §16).

Sizes and ``size.over_limit`` from the embedder's tokenizer say ``measured``; with it unavailable they say
``estimated``, everywhere they appear.
"""

import json
from pathlib import Path

from ragcourt.testing import FakeOllamaState
from tests.conftest import Run, audit_findings


def test_measured_through_ollama(
    project: Path, corpus: Path, run: Run, ollama: tuple[str, FakeOllamaState]
) -> None:
    url, state = ollama
    state.models["tiny-embed"] = 300
    (project / "ragcourt.toml").write_text(f'ollama_url = "{url}"\n[models]\nembedders = ["tiny-embed"]\n')
    code, out, _ = run("audit", corpus, "--chunker", "recursive:size=4000,overlap=0", "--json")
    assert code == 0
    data = json.loads(out)
    assert data["sizes"] == "measured" and data["limit"] == 300
    over = [f for f in audit_findings(data) if f["code"] == "size.over_limit"]
    assert over and all("the rest was cut (measured)" in f["detail"] for f in over)
    text = run("audit", corpus, "--chunker", "recursive:size=4000,overlap=0")[1]
    assert "Sizes: measured, by tiny-embed" in text and "estimated" not in text


def test_estimated_when_ollama_is_away(project: Path, corpus: Path, run: Run, no_network: list[str]) -> None:
    code, out, _ = run(
        "audit",
        corpus,
        "--embedder",
        "mxbai-embed-large",
        "--chunker",
        "recursive:size=4000,overlap=0",
        "--json",
    )
    data = json.loads(out)
    over = [f for f in audit_findings(data) if f["code"] == "size.over_limit"]
    assert code == 0 and data["sizes"] == "estimated" and data["limit"] == 512
    assert over and all("(estimated)" in f["detail"] for f in over)


def test_an_unknown_model_offline_skips_the_limit_check(
    project: Path, corpus: Path, run: Run, no_network: list[str]
) -> None:
    code, out, _ = run("audit", corpus, "--embedder", "some-new-model", "--chunker", "markdown")
    assert code == 0 and "size.over_limit is skipped" in out
