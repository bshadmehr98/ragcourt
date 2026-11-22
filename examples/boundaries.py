"""See the cuts: a document with its chunk boundaries marked.

What: where a chunker cuts one document, and which chunks a check flags.
How: ``ragcourt audit --show DOC``: ``⟦12⟧`` starts chunk 12, ``⟧`` ends a chunk, flags are named.
Why: a table split in two or a sentence cut in half is obvious once you see it on your own text.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    chunker = "fixed:size=40,overlap=0"
    code = main(
        [
            "audit",
            str(corpus_path()),
            "--embedder",
            "fake",
            "--chunker",
            chunker,
            "--show",
            "configuration.md",
            "-q",
        ]
    )
assert code == 0
