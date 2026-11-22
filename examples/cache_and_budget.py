"""The cache and the budget: a second run embeds nothing; a run that would take too long never starts.

What: embeddings are kept in plain files and never computed twice; ``--budget-minutes`` stops a run before
the step that would pass it, exit code 4, with nothing called complete.
How: two runs, counting the embedding calls the fake Ollama receives; then a run with a tiny budget.
Why: real runs take minutes; reruns should cost seconds, and a budget should hold.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project


def embedding_calls(requests: list[tuple[str, dict]]) -> int:  # type: ignore[type-arg]
    """How many embedding calls the fake Ollama received."""
    return sum(1 for path, _ in requests if path == "/api/embed")


with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)) as server:
    assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
    first = embedding_calls(server.requests)
    assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
    print(f"embedding calls: first run {first}, second run {embedding_calls(server.requests) - first}")
    assert embedding_calls(server.requests) == first
    assert main(["rank", str(corpus_path()), "--yes", "--budget-minutes", "0.0001", "-q"]) == 4
