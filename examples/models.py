"""Change a model: one command, comments kept, the new judge tested at once.

What: every model has a role (writer, judge, embedders, reranker, doctor); ``models`` shows them with where
each choice came from; ``models set`` changes one in ``ragcourt.toml``.
How: show the roles, set the judge, show again.
Why: nothing happens blindly: you see which model does what before it runs (D-030, D-031).
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)) as server:
    server.models["another-judge"] = 4096
    assert main(["models"]) == 0
    assert main(["models", "set", "judge", "another-judge", "-q"]) == 0
    print((Path(folder) / "ragcourt.toml").read_text())
