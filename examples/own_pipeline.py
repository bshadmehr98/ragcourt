"""Your own retrieval system, measured and blamed.

What: a pipeline ragcourt did not build (here a tiny keyword index standing in for your vector database)
    is asked every question, scored on the same held-out questions, and each of its misses gets a cause.
How: one function in ``ragcourt_stages/`` with ``@pipeline("name")``: a question in, your chunk texts out,
    best first. ``@pipeline_chunks`` lists every chunk you hold, so a chunker's cut can be told from a
    retrieval miss. Then ``ragcourt rank DOCS --pipeline name``.
Why: a leaderboard of other stages is advice; this is your system on your documents (change 0006).
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

MY_PIPELINE = f"""
from pathlib import Path

from ragcourt.stages import pipeline, pipeline_chunks

# Stand-in for your own system: paragraphs as chunks, ranked by the words they share with the question.
CHUNKS = []
for path in sorted(Path({str(corpus_path())!r}).glob("*.md")):
    CHUNKS += [part.strip() for part in path.read_text().split("\\n\\n") if len(part.strip()) > 80]


@pipeline("mine")
def mine(query: str, depth: int) -> list[str]:
    words = set(query.lower().split())
    ranked = sorted(CHUNKS, key=lambda chunk: -len(words & set(chunk.lower().split())))
    return ranked[:depth]


@pipeline_chunks("mine")
def mine_chunks() -> list[str]:
    return CHUNKS
"""

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    (Path(folder) / "ragcourt_stages").mkdir()
    (Path(folder) / "ragcourt_stages" / "mine.py").write_text(MY_PIPELINE)
    code = main(["rank", str(corpus_path()), "--pipeline", "mine", "--no-search", "--yes", "-q"])
    assert code == 0
    assert main(["explain", "-q"]) == 0
