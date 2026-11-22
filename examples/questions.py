"""Questions with gold quotes: written, filtered by a judge, split.

What: six categories of questions, each gold answer an exact quote, each drop with its reason.
How: ``ragcourt questions`` with a scripted writer and judge standing in for local models.
Why: gold that is a span of the source never depends on a chunker, so every chunker is judged on the same
questions; categories say which weakness each question tests.
"""

import tempfile
from pathlib import Path

from ragcourt.cli import main
from ragcourt.testing import ScriptedReplies, corpus_path, offline_project

# A writer that answers one kind of question without the documents: the judge drops those (too easy).
replies = ScriptedReplies(known={"Which number is given"})
with tempfile.TemporaryDirectory() as folder, offline_project(Path(folder), replies):
    assert main(["questions", str(corpus_path()), "-q"]) == 0
    assert main(["questions", "show", "--dropped", "--reason", "answerable"]) == 0
