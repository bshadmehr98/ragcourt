"""The HTML report: one file, no network.

What: every leaderboard with interval bars and ties, the ceilings, every miss with its quote shown on the
source text, the audit of the chosen chunker.
How: ``ragcourt rank --html`` (or ``ragcourt report`` for an earlier run).
Why: a file you can send or archive; it opens without the internet.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import corpus_path, offline_project

with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder)):
    assert main(["rank", str(corpus_path()), "--yes", "-q"]) == 0
    assert main(["report"]) == 0
    report = next((Path(folder) / ".ragcourt" / "runs").glob("*/report.html"))
    assert "http://" not in report.read_text() and "https://" not in report.read_text()
