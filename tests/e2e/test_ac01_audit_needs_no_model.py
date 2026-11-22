"""Guarantee 1: audit needs no key and no chat model (design §5, §16).

With every connection blocked, ``ragcourt audit`` on the bundled corpus still runs, labels sizes
estimated, and reports every check of §5.1 on the document planted for it.
"""

import json
from pathlib import Path

from tests.conftest import Run, audit_findings

CHUNKERS = [
    "--chunker",
    "fixed:size=40,overlap=0",
    "--chunker",
    "markdown",
    "--chunker",
    "recursive:size=4000,overlap=0",
]
PLANTED = {
    "cut.mid_sentence": "queues.md",
    "context.no_heading": "queues.md",
    "split.table": "configuration.md",
    "split.code": "install.md",
    "boilerplate.repeated": "configuration.md",
    "duplicate.near": "upgrading.md",
    "size.tiny": "index.md",
    "size.over_limit": "queues.md",
}


def test_audit_runs_offline_and_reports_every_check(
    project: Path, corpus: Path, run: Run, no_network: list[str]
) -> None:
    code, out, _ = run("audit", corpus, "--embedder", "mxbai-embed-large", *CHUNKERS, "--json")
    assert code == 0
    data = json.loads(out)
    assert data["sizes"] == "estimated" and "did not answer" in data["note"]
    assert all(result["size"]["label"] == "estimated" for result in data["chunkers"])
    found = {(f["code"], f["document"]) for f in audit_findings(data)}
    for check, document in PLANTED.items():
        assert (check, document) in found, check
    assert no_network, "the audit should have tried Ollama for token counts"


def test_the_text_output_has_tables_examples_and_a_legend(
    project: Path, corpus: Path, run: Run, no_network: list[str]
) -> None:
    code, out, _ = run("audit", corpus, *CHUNKERS)
    assert code == 0
    assert "Sizes: estimated (characters / 4)" in out
    assert "Findings: chunks flagged (share)" in out and "Examples: markdown" in out
    assert "Legend:" in out and "flags a chunk that ends in the middle of a sentence" in out
    quiet = run("audit", corpus, *CHUNKERS, "-q")[1]
    assert "Legend:" not in quiet
