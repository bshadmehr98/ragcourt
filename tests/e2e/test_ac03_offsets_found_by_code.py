"""Guarantee 3: offsets are found by code (design §4.2, §16).

Overlapping chunks, repeated text and whitespace-changed chunks map to the right spans; a chunk not in the
source fails with ``ChunkNotInSource`` naming the chunk.
"""

import re
from pathlib import Path

from tests.conftest import Run

CHUNKERS = """
from ragcourt.stages import chunker


@chunker("overlapping")
def overlapping(text: str) -> list[str]:
    return ["alpha beta", "beta gamma", "alpha beta"]


@chunker("reflowed")
def reflowed(text: str) -> list[str]:
    return [" ".join(text.split())]


@chunker("inventing")
def inventing(text: str) -> list[str]:
    return ["Summary: not in the text"]
"""


def setup(project: Path, tmp_path: Path) -> Path:
    corpus = tmp_path / "docs"
    corpus.mkdir()
    (corpus / "doc.md").write_text("alpha beta gamma alpha beta\nend\n")
    (project / "ragcourt_stages").mkdir()
    (project / "ragcourt_stages" / "mine.py").write_text(CHUNKERS)
    return corpus


def test_spans_and_the_failure(project: Path, tmp_path: Path, run: Run, registry: None) -> None:
    corpus = setup(project, tmp_path)
    code, out, _ = run(
        "audit", corpus, "--embedder", "fake", "--chunker", "overlapping", "--show", "doc.md", "-q"
    )
    assert code == 0
    marked = re.sub(r"⟦(\d+)[^⟧]*⟧", r"⟦\1⟧", out.split("---\n")[-1])
    assert marked.startswith("⟦0⟧alpha ⟦1⟧beta⟧ gamma⟧ ⟦2⟧alpha beta⟧\nend")
    code, out, _ = run(
        "audit", corpus, "--embedder", "fake", "--chunker", "reflowed", "--show", "doc.md", "-q"
    )
    marked = re.sub(r"⟦(\d+)[^⟧]*⟧", r"⟦\1⟧", out.split("---\n")[-1])
    assert code == 0 and marked.startswith("⟦0⟧alpha beta gamma alpha beta\nend⟧")
    code, _, err = run("audit", corpus, "--embedder", "fake", "--chunker", "inventing")
    assert code == 1
    assert "Chunker 'inventing' returned chunk 0 of 'doc.md'" in err and "Summary: not in the text" in err
