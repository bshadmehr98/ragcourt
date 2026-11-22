"""Rank pipelines: leaderboards with intervals, ties said, every miss blamed.

What: embedders, then chunkers, retrievers and rerankers, each step on dev questions, every number on
held-out questions with its 95% interval; "no significant difference" when that is the truth.
How: ``ragcourt rank`` on the bundled corpus with scripted models and the fake embedders.
Why: a two-point gap on forty questions is noise; the interval says so.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
